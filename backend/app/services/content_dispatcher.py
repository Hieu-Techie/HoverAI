"""Module 3: điều phối bộ xử lý theo loại nội dung của URL."""

from typing import Any, Dict, Optional

from app.services.content_classifier import ContentType, detect_content_type
from app.services.content_extractor import (
    ContentExtractionError,
    extract_article_content,
    extract_article_content_from_html,
)
from app.services.article_summarizer import summarize_article
from app.services.product_extractor import (
    extract_product_from_html,
    fetch_and_extract_product,
)
from app.services.product_summarizer import summarize_product


class UnsupportedContentTypeError(Exception):
    """Lỗi dùng khi loại nội dung đã được nhận diện nhưng chưa có processor."""

    def __init__(self, content_type: ContentType):
        self.content_type = content_type
        super().__init__(f"CONTENT_TYPE_{content_type.value.upper()}_UNSUPPORTED")


# ---------------------------------------------------------------------------
# FR3.1 — bài viết / trang thông tin
# ---------------------------------------------------------------------------

async def _dispatch_article(
    result: Dict[str, Any],
    content_type: ContentType,
    gemini_api_key: Optional[str],
) -> Dict[str, Any]:
    """FR3.1: gắn content type, summary và tiêu đề chuẩn hóa tiếng Việt vào kết quả bài viết."""
    result["content_type"] = content_type.value
    gemini_result = await summarize_article(
        result.get("title", ""),
        result.get("text", ""),
        gemini_api_key,
    )
    if isinstance(gemini_result, dict):
        result["summary"] = gemini_result.get("summary")
        # Ưu tiên tiêu đề đã chuẩn hóa tiếng Việt từ AI nếu có
        title_vi = gemini_result.get("title_vi")
        if title_vi:
            result["title_vi"] = title_vi   # giữ cả bản gốc cho debug
            result["title"] = title_vi
    else:
        result["summary"] = gemini_result
    return result


# ---------------------------------------------------------------------------
# FR3.2 — trang sản phẩm
# ---------------------------------------------------------------------------

def _product_to_unified_response(
    product: Dict[str, Any],
    summary: Optional[str],
    url: str,
    name_vi: Optional[str] = None,
) -> Dict[str, Any]:
    """FR3.2: chuyển đổi dict sản phẩm về schema chung (Phương án A — backward compat).

    name_vi: tên sản phẩm đã chuẩn hóa tiếng Việt từ Gemini (ưu tiên hơn tên gốc).
    """
    display_name = name_vi or product.get("name") or "Sản phẩm"
    return {
        "url": url,
        "method": "structured_data",
        "title": display_name,
        "text": product.get("description") or "",
        "metadata": {
            "price": product.get("price"),
            "price_display": product.get("price_display"),
            "currency": product.get("currency"),
            "rating": product.get("rating"),
            "rating_display": product.get("rating_display"),
            "review_count": product.get("review_count"),
            "brand": product.get("brand"),
            "image_url": product.get("image_url"),
            "site_name": product.get("site_name"),
            "sku": product.get("sku"),
            "extraction_note": product.get("extraction_note"),
            "name_original": product.get("name"),  # tên gốc để debug
        },
        "content_type": ContentType.PRODUCT.value,
        "summary": summary,
    }


async def _dispatch_product_from_html(
    url: str,
    html: str,
    gemini_api_key: Optional[str],
) -> Dict[str, Any]:
    """FR3.2: trích xuất sản phẩm từ HTML đã render (ưu tiên từ extension)."""
    product = extract_product_from_html(url, html)
    gemini_result = await summarize_product(product, gemini_api_key)
    summary = gemini_result.get("summary") if isinstance(gemini_result, dict) else gemini_result
    name_vi = gemini_result.get("name_vi") if isinstance(gemini_result, dict) else None
    return _product_to_unified_response(product, summary, url, name_vi)


async def _dispatch_product_from_url(
    url: str,
    gemini_api_key: Optional[str],
) -> Dict[str, Any]:
    """FR3.2: backend tự tải HTML rồi trích xuất sản phẩm."""
    product = await fetch_and_extract_product(url)
    gemini_result = await summarize_product(product, gemini_api_key)
    summary = gemini_result.get("summary") if isinstance(gemini_result, dict) else gemini_result
    name_vi = gemini_result.get("name_vi") if isinstance(gemini_result, dict) else None
    return _product_to_unified_response(product, summary, url, name_vi)


# ---------------------------------------------------------------------------
# Dispatcher chính — entry points từ routes
# ---------------------------------------------------------------------------

async def dispatch_url_content(
    url: str, gemini_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """FR3.1/FR3.2: phân loại URL rồi điều phối sang processor phù hợp."""
    content_type = detect_content_type(url)
    if content_type == ContentType.VIDEO:
        raise UnsupportedContentTypeError(content_type)
    if content_type == ContentType.PRODUCT:
        return await _dispatch_product_from_url(url, gemini_api_key)
    # ARTICLE hoặc UNKNOWN → xử lý như bài viết
    result = await extract_article_content(url)
    return await _dispatch_article(result, content_type, gemini_api_key)


async def dispatch_html_content(
    url: str,
    html: str,
    page_title: str = "",
    gemini_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """FR3.1/FR3.2: phân loại HTML/URL rồi điều phối DOM đã render sang processor."""
    content_type = detect_content_type(url, html)
    if content_type == ContentType.VIDEO:
        raise UnsupportedContentTypeError(content_type)
    if content_type == ContentType.PRODUCT:
        return await _dispatch_product_from_html(url, html, gemini_api_key)
    # ARTICLE hoặc UNKNOWN → xử lý như bài viết
    result = await extract_article_content_from_html(url, html, page_title)
    return await _dispatch_article(result, content_type, gemini_api_key)
