"""Jina Reader — shared HTTP client dùng chung cho tất cả processor.

FR3.1 (bài viết), FR3.2 (sản phẩm) và FR3.3 (video, sắp tới) đều cần gọi
r.jina.ai để render JavaScript khi static fetch thất bại.
Module này cung cấp một điểm duy nhất để quản lý timeout, header, retry.
"""

import asyncio
import re
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JINA_BASE_URL = "https://r.jina.ai"
JINA_TIMEOUT_ARTICLE = 30    # bài viết cần thêm thời gian vì lấy toàn văn
JINA_TIMEOUT_PRODUCT = 15    # sản phẩm chỉ cần tên/mô tả nhanh
JINA_MIN_TEXT_LENGTH = 100   # bỏ qua nếu Jina trả về quá ít nội dung

# Dùng httpx.get sync trong executor để bypass Cloudflare bot detection.
# QUAN TRỌNG: KHÔNG set custom User-Agent vì Jina/Cloudflare block Chrome UA giả mạo.
# httpx default UA (python-httpx/x.x) được phép qua.
_JINA_HEADERS = {
    "Accept": "text/markdown, text/plain;q=0.9, */*;q=0.8",
    "X-Return-Format": "markdown",
}

# Regex strip hậu tố site kiểu "| Shopee Việt Nam" hay "- Lazada VN"
_SITE_SUFFIX_RE = re.compile(r"\s*[\|\u2013\-]\s*[^|\u2013\-]{2,40}$")


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

async def fetch_jina_markdown(url: str, timeout: int = JINA_TIMEOUT_PRODUCT) -> Optional[str]:
    """Gọi Jina Reader, trả về raw markdown text hoặc None nếu thất bại/403.

    Sử dụng httpx sync trong executor để bypass Cloudflare bot detection —
    httpx.AsyncClient bị Jina block (TLS fingerprint khác), còn httpx.Client
    (sync) được qua.

    Args:
        url:     URL gốc cần render (KHÔNG phải jina URL).
        timeout: Tổng timeout tính bằng giây.

    Returns:
        Chuỗi markdown text, hoặc None nếu thất bại/quá ngắn.
    """
    jina_url = f"{JINA_BASE_URL}/{url}"

    def _fetch_sync() -> Optional[str]:
        try:
            resp = httpx.get(
                jina_url,
                headers=_JINA_HEADERS,
                timeout=timeout,
                follow_redirects=True,
            )
            if resp.status_code >= 400:
                return None
            text = resp.text.strip()
            return text if len(text) >= JINA_MIN_TEXT_LENGTH else None
        except Exception:
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_sync)


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

