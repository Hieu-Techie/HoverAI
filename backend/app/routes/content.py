from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl
from app.services.content_dispatcher import (
    UnsupportedContentTypeError,
    dispatch_html_content,
    dispatch_url_content,
)
from app.services.content_extractor import MAX_HTML_BYTES, ContentExtractionError
from app.services.product_extractor import (
    extract_product_from_html,
    fetch_and_extract_product,
)
from app.services.product_summarizer import summarize_product

# Module 3, FR3.1/FR3.2: API nhận URL hoặc HTML đã được Chrome render.
router = APIRouter()


# ---------------------------------------------------------------------------
# FR3.1 — bài viết
# ---------------------------------------------------------------------------

class ContentExtractionRequest(BaseModel):
    """FR3.1: request để backend tự tải HTML từ URL công khai."""
    url: HttpUrl
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)


class ContentExtractionResponse(BaseModel):
    """FR3.1/FR3.2: kết quả chung sau khi dispatcher xử lý — dùng chung cho article và product."""
    url: HttpUrl
    method: str
    title: str
    text: str
    metadata: dict
    content_type: str
    summary: Optional[str] = None


class HtmlContentExtractionRequest(BaseModel):
    """FR3.1: request ưu tiên cho extension, dùng DOM đã render trong Chrome."""
    url: HttpUrl
    html: str = Field(min_length=1, max_length=MAX_HTML_BYTES)
    page_title: str = Field(default="", max_length=500)
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)


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

class ProductExtractionRequest(BaseModel):
    """FR3.2: request trích xuất sản phẩm — có thể gửi HTML sẵn hoặc để backend tự tải."""
    url: HttpUrl
    html: Optional[str] = Field(default=None, max_length=MAX_HTML_BYTES)
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)


class ProductExtractionResponse(BaseModel):
    """FR3.2: kết quả trích xuất sản phẩm với các trường chuyên biệt."""
    url: HttpUrl
    content_type: str = "product"
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[str] = None
    price_display: Optional[str] = None
    currency: Optional[str] = None
    rating: Optional[str] = None
    rating_display: Optional[str] = None
    review_count: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    site_name: Optional[str] = None
    sku: Optional[str] = None
    summary: Optional[str] = None


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
            "summary": summary,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PRODUCT_EXTRACTION_ERROR: {exc}") from exc
