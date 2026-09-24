from fastapi import APIRouter, HTTPException

from app.models.content import ContentExtractionRequest, ContentExtractionResponse, HtmlContentExtractionRequest
from app.models.product import ProductExtractionRequest, ProductExtractionResponse
from app.models.video import VideoMetadataRequest, VideoMetadataResponse
from app.services.dispatch.content_dispatcher import (
    UnsupportedContentTypeError,
    dispatch_html_content,
    dispatch_url_content,
)
from app.services.extractors.content_extractor import MAX_HTML_BYTES, ContentExtractionError
from app.services.extractors.product_extractor import (
    extract_product_from_html,
    fetch_and_extract_product,
)
from app.services.summarizers.product_summarizer import summarize_product
from app.services.summarizers.video_summarizer import summarize_video

# Module 3, FR3.1/FR3.2/FR3.3/FR3.4: API nhận URL hoặc HTML đã được Chrome render.
router = APIRouter()


# ---------------------------------------------------------------------------
# FR3.1 — bài viết
# ---------------------------------------------------------------------------


@router.post("/api/extract-content", response_model=ContentExtractionResponse)
async def extract_content(request: ContentExtractionRequest):
    """FR3.1/FR3.2: nhận URL và chuyển việc xử lý cho content dispatcher."""
    try:
        return await dispatch_url_content(str(request.url), request.gemini_api_key)
    except UnsupportedContentTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContentExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/extract-content-from-html", response_model=ContentExtractionResponse)
async def extract_content_from_html(request: HtmlContentExtractionRequest):
    """FR3.1/FR3.2: nhận DOM đã render và chuyển việc xử lý cho content dispatcher."""
    try:
        return await dispatch_html_content(
            str(request.url),
            request.html,
            request.page_title,
            request.gemini_api_key,
        )
    except UnsupportedContentTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# FR3.2 — endpoint riêng cho sản phẩm (gọi trực tiếp, bypass classifier)
# ---------------------------------------------------------------------------




@router.post("/api/extract-product", response_model=ProductExtractionResponse)
async def extract_product(request: ProductExtractionRequest):
    """FR3.2: trích xuất thông tin sản phẩm trực tiếp — không qua classifier.

    Dùng HTML đã render (nếu extension gửi) hoặc tự tải HTML từ URL.
    Endpoint này luôn xử lý như sản phẩm bất kể classifier phân loại gì.
    """
    try:
        if request.html:
            product = extract_product_from_html(str(request.url), request.html)
        else:
            product = await fetch_and_extract_product(str(request.url))

        summary = await summarize_product(product, request.gemini_api_key)
        return {
            "url": str(request.url),
            "content_type": "product",
            "name": product.get("name"),
            "brand": product.get("brand"),
            "price": product.get("price"),
            "price_display": product.get("price_display"),
            "currency": product.get("currency"),
            "rating": product.get("rating"),
            "rating_display": product.get("rating_display"),
            "review_count": product.get("review_count"),
            "description": product.get("description"),
            "image_url": product.get("image_url"),
            "site_name": product.get("site_name"),
            "sku": product.get("sku"),
            "summary": summary.get("summary") if isinstance(summary, dict) else summary,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PRODUCT_EXTRACTION_ERROR: {exc}") from exc


# ---------------------------------------------------------------------------
# FR3.4 — tóm tắt dự đoán từ tiêu đề/mô tả (không có transcript)
# ---------------------------------------------------------------------------


@router.post("/api/summarize-from-metadata", response_model=VideoMetadataResponse)
async def summarize_from_metadata(request: VideoMetadataRequest):
    """FR3.4: tóm tắt video từ tiêu đề/mô tả khi không có transcript thực.

    Luôn đánh dấu is_prediction=True và kèm cảnh báo clickbait.
    Dùng khi FR3.3 không lấy được transcript (video tắt phụ đề, nền tảng không hỗ trợ...).
    """
    result = await summarize_video(
        title=request.title,
        transcript=None,  # FR3.4 — không có transcript
        description=request.description,
        channel=request.channel or "",
        platform=request.platform or "video",
        api_key=request.gemini_api_key,
    )

    # Xác định cảnh báo tùy theo nguồn dữ liệu
    if request.description and len(request.description.strip()) > 30:
        warning = (
            "Tóm tắt dựa trên mô tả video, không phải nội dung thực. "
            "Có thể không phản ánh đầy đủ nội dung."
        )
    else:
        warning = (
            "Tóm tắt dự đoán chỉ dựa trên tiêu đề. "
            "Có thể chứa yếu tố giật gân — chỉ mang tính tham khảo."
        )

    return {
        "title_vi": result.get("title_vi") if result else None,
        "summary": result.get("summary") if result else None,
        "is_prediction": True,
        "warning": warning,
    }
