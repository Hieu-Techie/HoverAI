"""Jina Reader — shared HTTP client dùng chung cho tất cả processor.

FR3.1 (bài viết), FR3.2 (sản phẩm) và FR3.3 (video, sắp tới) đều cần gọi
r.jina.ai để render JavaScript khi static fetch thất bại.
Module này cung cấp một điểm duy nhất để quản lý timeout, header, retry.
"""

import asyncio
import re
from typing import Optional

import aiohttp

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JINA_BASE_URL = "https://r.jina.ai"
JINA_TIMEOUT_ARTICLE = 30    # bài viết cần thêm thời gian vì lấy toàn văn
JINA_TIMEOUT_PRODUCT = 15    # sản phẩm chỉ cần tên/mô tả nhanh
JINA_MIN_TEXT_LENGTH = 100   # bỏ qua nếu Jina trả về quá ít nội dung

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_JINA_HEADERS = {
    "Accept": "text/markdown, text/plain;q=0.9",
    "User-Agent": _USER_AGENT,
}

# Regex strip hậu tố site kiểu "| Shopee Việt Nam" hay "- Lazada VN"
_SITE_SUFFIX_RE = re.compile(r"\s*[\|\u2013\-]\s*[^|\u2013\-]{2,40}$")


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

async def fetch_jina_markdown(url: str, timeout: int = JINA_TIMEOUT_PRODUCT) -> Optional[str]:
    """Gọi Jina Reader, trả về raw markdown text hoặc None nếu thất bại/403.

    Args:
        url:     URL gốc cần render (KHÔNG phải jina URL).
        timeout: Tổng timeout tính bằng giây. Dùng JINA_TIMEOUT_ARTICLE cho
                 bài viết dài, JINA_TIMEOUT_PRODUCT cho trang sản phẩm.

    Returns:
        Chuỗi markdown text, hoặc None nếu:
        - Jina trả về status >= 400
        - Xảy ra lỗi network/timeout
        - Nội dung quá ngắn (< JINA_MIN_TEXT_LENGTH ký tự)
    """
    jina_url = f"{JINA_BASE_URL}/{url}"
    try:
        _timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=_timeout, headers=_JINA_HEADERS) as session:
            async with session.get(jina_url) as resp:
                if resp.status >= 400:
                    return None
                text = (await resp.read()).decode("utf-8", errors="replace").strip()
    except (asyncio.TimeoutError, aiohttp.ClientError, Exception):
        return None

    return text if len(text) >= JINA_MIN_TEXT_LENGTH else None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_title_from_markdown(markdown: str, strip_site_suffix: bool = False) -> Optional[str]:
    """Tìm tiêu đề/tên trong markdown do Jina trả về.

    Ưu tiên theo thứ tự:
    1. Dòng bắt đầu bằng "Title:" (Jina metadata header)
    2. Heading Markdown đầu tiên (# ...)

    Args:
        markdown:           Raw markdown text từ Jina.
        strip_site_suffix:  Nếu True, strip hậu tố "| Tên site" / "- Tên site"
                            — hữu ích cho trang sản phẩm.

    Returns:
        Chuỗi tiêu đề sạch (≤ 200 ký tự) hoặc None nếu không tìm được.
    """
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        candidate: Optional[str] = None

        if stripped.lower().startswith("title:"):
            candidate = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()

        if candidate:
            if strip_site_suffix:
                candidate = _SITE_SUFFIX_RE.sub("", candidate).strip()
            if len(candidate) > 10:
                return candidate[:200]

    return None


def parse_first_paragraph(markdown: str, min_len: int = 30, max_len: int = 500) -> Optional[str]:
    """Lấy đoạn văn đầu tiên có nghĩa từ markdown — dùng làm mô tả sản phẩm.

    Bỏ qua heading, ảnh, link, table. Trả về None nếu không tìm thấy.
    """
    for line in markdown.splitlines():
        stripped = line.strip()
        if (
            len(stripped) >= min_len
            and not stripped.startswith("#")
            and not stripped.startswith("!")
            and not stripped.startswith("[")
            and not stripped.startswith("|")
            and "http" not in stripped[:20]
        ):
            return stripped[:max_len]
    return None

