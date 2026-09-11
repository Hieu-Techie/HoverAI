import asyncio
from typing import Any, Dict, Optional
import aiohttp
import trafilatura
from bs4 import BeautifulSoup
from trafilatura import extract_metadata

try:
    from newspaper import Article
except ImportError:
    Article = None

from app.services.jina_reader import (
    JINA_TIMEOUT_ARTICLE,
    fetch_jina_markdown,
    parse_title_from_markdown,
)

# Module 3, FR3.1: tải và trích xuất nội dung bài viết từ HTML công khai
# hoặc DOM đã render do extension gửi lên.
MAX_HTML_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

class ContentExtractionError(Exception):
    """FR3.1: lỗi có mã để route trả nguyên nhân phù hợp cho client."""

    pass


def _is_bot_challenge(html: str) -> bool:
    """FR3.1: nhận diện một số trang challenge thay vì coi chúng là bài viết."""
    lowered_html = html.lower()
    visible_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return (
        "just a moment" in lowered_html
        or "cf-chl" in lowered_html
        or ("cloudflare" in lowered_html and len(visible_text) < 1000)
    )


def _is_empty_document(html: str) -> bool:
    """FR3.1: nhận diện response chỉ có menu hoặc document chưa có nội dung."""
    soup = BeautifulSoup(html, "html.parser")
    visible_text = soup.get_text(" ", strip=True)
    return len(soup.select("p")) == 0 and len(visible_text) < 1000


def _is_low_quality_content(text: str, html: str) -> bool:
    """FR3.1: nhận diện output thiên về menu thay vì nội dung chính."""
    soup = BeautifulSoup(html, "html.parser")
    text_length = len(text.strip())
    navigation_elements = len(soup.select("nav, header, footer, aside"))
    link_elements = len(soup.select("a"))
    navigation_text = " ".join(
        element.get_text(" ", strip=True)
        for element in soup.select("nav, header, footer, aside")
    )

    # Một bài ngắn vẫn hợp lệ; chỉ loại khi nó đi kèm nhiều cấu trúc điều hướng.
    if text_length < 300 and (navigation_elements >= 2 or link_elements >= 8):
        return True
    return bool(
        navigation_text
        and text_length < 1000
        and len(navigation_text) / text_length > 0.5
    )

async def _fetch_html(url: str) -> str:
    """FR3.1: tải HTML, giới hạn kích thước và retry response rỗng/challenge."""
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_SECONDS)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
    }
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status >= 400:
                        raise ContentExtractionError(f"SOURCE_HTTP_{response.status}")
                    content_type = response.headers.get("Content-Type", "")
                    if content_type and "html" not in content_type.lower():
                        raise ContentExtractionError("SOURCE_NOT_HTML")
                    body = await response.content.read(MAX_HTML_BYTES + 1)
                    if len(body) > MAX_HTML_BYTES:
                        raise ContentExtractionError("SOURCE_TOO_LARGE")
                    html = body.decode(response.charset or "utf-8", errors="replace")
                    if _is_bot_challenge(html) or _is_empty_document(html):
                        if attempt < 2:
                            await asyncio.sleep(0.5)
                            continue
                        if _is_bot_challenge(html):
                            raise ContentExtractionError("SOURCE_BOT_CHALLENGE")
                        raise ContentExtractionError("SOURCE_CONTENT_EMPTY")
                    return html
        except asyncio.TimeoutError as exc:
            raise ContentExtractionError("SOURCE_TIMEOUT") from exc
        except aiohttp.ClientError as exc:
            raise ContentExtractionError("SOURCE_UNAVAILABLE") from exc

    raise ContentExtractionError("SOURCE_BOT_CHALLENGE")


async def _extract_with_jina(url: str) -> Optional[Dict[str, Any]]:
    """FR3.1: fallback cuối dùng jina_reader khi nguồn/parser local thất bại."""
    markdown = await fetch_jina_markdown(url, timeout=JINA_TIMEOUT_ARTICLE)
    if not markdown:
        return None

    title = parse_title_from_markdown(markdown, strip_site_suffix=False) or ""
    return {
        "method": "jina_reader",
        "title": title,
        "text": markdown,
        "metadata": {},
        "url": url,
    }

def _metadata_to_dict(html: str) -> Dict[str, Optional[str]]:
    """FR3.1: lấy author, date, description, site, category và tags."""
    metadata = extract_metadata(html)
    if metadata is None:
        return {}
    return {
        "author": metadata.author,
        "date": metadata.date,
        "description": metadata.description,
        "sitename": metadata.sitename,
        "categories": metadata.categories,
        "tags": metadata.tags,
    }

def _extract_with_trafilatura(html: str) -> Optional[Dict[str, Any]]:
    """FR3.1: ưu tiên Trafilatura để loại menu, footer, quảng cáo và lấy bài chính."""
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        output_format="txt",
    )
    if not text or len(text.strip()) < 80:
        return None
    metadata = _metadata_to_dict(html)
    document_metadata = extract_metadata(html)
    title = document_metadata.title if document_metadata else None
    return {
        "method": "trafilatura",
        "title": title or "",
        "text": text.strip(),
        "metadata": metadata,
    }

def _extract_with_newspaper(url: str, html: str) -> Optional[Dict[str, Any]]:
    """FR3.1: fallback Newspaper3k khi Trafilatura không lấy được nội dung."""
    if Article is None:
        return None
    article = Article(url)
    article.set_html(html)
    article.parse()
    text = (article.text or "").strip()
    if not text:
        soup = BeautifulSoup(html, "html.parser")
        content_root = soup.select_one("article, main") or soup
        text = "\n\n".join(
            paragraph.get_text(" ", strip=True)
            for paragraph in content_root.select("p")
            if paragraph.get_text(" ", strip=True)
        )
    if not text:
        return None
    return {
        "method": "newspaper3k",
        "title": (article.title or "").strip(),
        "text": text,
        "metadata": {
            "author": ", ".join(article.authors) if article.authors else None,
            "date": article.publish_date.isoformat() if article.publish_date else None,
            "description": None,
            "sitename": None,
            "categories": None,
            "tags": None,
        },
    }

async def extract_article_content(url: str) -> Dict[str, Any]:
    """FR3.1: luồng backend tự tải URL rồi trích xuất bài viết."""
    try:
        html = await _fetch_html(url)
        return await extract_article_content_from_html(url, html)
    except ContentExtractionError:
        result = await _extract_with_jina(url)
        if result is not None:
            return result
        raise


async def extract_article_content_from_html(
    url: str, html: str, page_title: str = ""
) -> Dict[str, Any]:
    """FR3.1: luồng ưu tiên cho extension với HTML đã được trình duyệt render."""
    if not html.strip():
        raise ContentExtractionError("HTML_EMPTY")
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ContentExtractionError("HTML_TOO_LARGE")
    if _is_bot_challenge(html):
        raise ContentExtractionError("SOURCE_BOT_CHALLENGE")

    result = _extract_with_trafilatura(html)
    if result is not None and (
        _is_low_quality_content(result["text"], html)
    ):
        result = None
    if result is None:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _extract_with_newspaper, url, html)
    if result is not None and _is_low_quality_content(result["text"], html):
        result = None
    if result is None:
        result = await _extract_with_jina(url)
    if result is None:
        raise ContentExtractionError("CONTENT_NOT_FOUND")
    if not result["title"]:
        result["title"] = page_title.strip()
    result["url"] = url
    return result
