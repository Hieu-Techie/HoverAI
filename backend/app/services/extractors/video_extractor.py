"""FR3.3: trích xuất transcript/metadata video từ mọi nền tảng phổ biến.

Pipeline:
- YouTube            → transcript qua youtube-transcript-api + oEmbed metadata
- Vimeo/Dailymotion/
  TikTok/Twitch      → metadata qua oEmbed API (không cần API key)
- Facebook/Instagram/
  Tất cả còn lại     → fetch HTML, parse OG tags + meta description
- File .mp4 v.v.     → lấy tên file từ URL
"""

import asyncio
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup
from youtube_transcript_api import (  # type: ignore[import]
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

# Ngôn ngữ ưu tiên khi lấy transcript YouTube
PREFERRED_LANGS = ["vi", "en"]

# Giới hạn transcript gửi cho Gemini (ký tự)
MAX_TRANSCRIPT_CHARS = 12_000

# Giới hạn mô tả (description) gửi cho Gemini khi không có transcript
MAX_DESCRIPTION_CHARS = 3_000

# Timeout (giây)
OEMBED_TIMEOUT_SECONDS = 5
PAGE_FETCH_TIMEOUT_SECONDS = 8
MAX_HTML_BYTES = 512_000  # 512 KB — đủ để đọc <head>

# oEmbed endpoint của các nền tảng phổ biến (không cần API key)
_OEMBED_PROVIDERS: Dict[str, str] = {
    "youtube.com":     "https://www.youtube.com/oembed",
    "youtu.be":        "https://www.youtube.com/oembed",
    "vimeo.com":       "https://vimeo.com/api/oembed.json",
    "dailymotion.com": "https://www.dailymotion.com/services/oembed",
    "tiktok.com":      "https://www.tiktok.com/oembed",
    "twitch.tv":       "https://www.twitch.tv/oembed",
}

# Tên hiển thị thân thiện cho từng nền tảng
_PLATFORM_NAMES: Dict[str, str] = {
    "youtube.com":    "YouTube",
    "youtu.be":       "YouTube",
    "vimeo.com":      "Vimeo",
    "dailymotion.com":"Dailymotion",
    "tiktok.com":     "TikTok",
    "twitch.tv":      "Twitch",
    "facebook.com":   "Facebook",
    "fb.watch":       "Facebook",
    "instagram.com":  "Instagram",
    "twitter.com":    "Twitter/X",
    "x.com":          "Twitter/X",
    "rumble.com":     "Rumble",
    "bilibili.com":   "Bilibili",
}

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

# ---------------------------------------------------------------------------
# Helpers: YouTube video ID
# ---------------------------------------------------------------------------

_VIDEO_ID_PATTERNS = [
    r"youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> Optional[str]:
    """Bóc tách video ID từ YouTube URL. Trả về None nếu không phải YouTube."""
    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Helpers: phát hiện nền tảng
# ---------------------------------------------------------------------------

def _detect_platform(hostname: str) -> str:
    """Tên nền tảng thân thiện từ hostname (ví dụ: 'www.youtube.com' → 'YouTube')."""
    host = hostname.lower().removeprefix("www.")
    for domain, name in _PLATFORM_NAMES.items():
        if host == domain or host.endswith(f".{domain}"):
            return name
    return host or "Video"


def _is_youtube(hostname: str) -> bool:
    h = hostname.lower().removeprefix("www.")
    return h in ("youtube.com", "youtu.be") or h.endswith(".youtube.com")


# ---------------------------------------------------------------------------
# Lấy metadata qua oEmbed (không cần API key)
# ---------------------------------------------------------------------------

async def _fetch_oembed(url: str, hostname: str) -> Optional[Dict[str, str]]:
    """Thử lấy title, channel, thumbnail từ oEmbed nếu platform hỗ trợ.

    Trả về None nếu platform không trong danh sách hoặc request thất bại.
    """
    host = hostname.lower().removeprefix("www.")
    endpoint = None
    for domain, ep in _OEMBED_PROVIDERS.items():
        if host == domain or host.endswith(f".{domain}"):
            endpoint = ep
            break
    if not endpoint:
        return None

    timeout = aiohttp.ClientTimeout(total=OEMBED_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                endpoint, params={"url": url, "format": "json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    return {
                        "title": data.get("title", ""),
                        "channel": data.get("author_name", ""),
                        "thumbnail_url": data.get("thumbnail_url", ""),
                        "description": data.get("description", ""),
                    }
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Lấy metadata từ HTML OG tags (fallback chung)
# ---------------------------------------------------------------------------

async def _fetch_og_metadata(url: str) -> Dict[str, str]:
    """Fetch HTML trang, parse OG/meta tags để lấy title + description.

    Không raise — trả về dict rỗng nếu thất bại.
    """
    timeout = aiohttp.ClientTimeout(total=PAGE_FETCH_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(
            timeout=timeout, headers=_FETCH_HEADERS
        ) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status >= 400:
                    return {}
                raw = await resp.content.read(MAX_HTML_BYTES)
                html = raw.decode("utf-8", errors="replace")
    except Exception:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    def _og(prop: str) -> str:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return (tag.get("content") or "") if tag else ""  # type: ignore[union-attr]

    title = (
        _og("og:title")
        or _og("twitter:title")
        or (soup.title.string.strip() if soup.title else "")
    )
    description = (
        _og("og:description")
        or _og("twitter:description")
        or _og("description")
    )
    channel = _og("og:site_name")
    thumbnail = _og("og:image") or _og("twitter:image")

    return {
        "title": title[:200],
        "channel": channel,
        "thumbnail_url": thumbnail,
        "description": description[:MAX_DESCRIPTION_CHARS],
    }


# ---------------------------------------------------------------------------
# Lấy transcript (sync, chạy trong executor) — youtube-transcript-api v1.x
# ---------------------------------------------------------------------------

def _fetch_transcript_sync(video_id: str) -> Dict[str, Any]:
    """Lấy transcript YouTube — tương thích youtube-transcript-api v1.x.

    Chiến lược:
    1. Thử ngôn ngữ ưu tiên [vi, en] — transcript chất lượng cao nhất cho Gemini.
    2. Nếu không có → lấy BẤT KỲ ngôn ngữ nào có sẵn (Hàn, Nhật, Tây Ban Nha, ...).
       Gemini vẫn có thể đọc và tóm tắt transcript đa ngôn ngữ.
    3. Chỉ trả TRANSCRIPT_DISABLED nếu kênh/video tắt hoàn toàn phụ đề.
    """
    api = YouTubeTranscriptApi()

    result = None
    lang_code = None

    # Bước 1: thử ngôn ngữ ưu tiên (vi, en)
    try:
        result = api.fetch(video_id, languages=PREFERRED_LANGS)
        lang_code = getattr(result, "language_code", "vi/en")
    except NoTranscriptFound:
        pass
    except TranscriptsDisabled:
        return {"transcript": None, "note": "TRANSCRIPT_DISABLED"}
    except Exception:
        return {"transcript": None, "note": "TRANSCRIPT_ERROR"}

    # Bước 2: không có vi/en → thử liệt kê và lấy ngôn ngữ đầu tiên có sẵn
    if result is None:
        try:
            transcript_list = api.list(video_id)
            # Ưu tiên: manual > auto-generated, sau đó lấy bất kỳ
            chosen = None
            for t in transcript_list:
                if chosen is None:
                    chosen = t
                elif not chosen.is_generated and t.is_generated:
                    # giữ manual thay vì auto
                    pass
                elif chosen.is_generated and not t.is_generated:
                    chosen = t
            if chosen is not None:
                result = api.fetch(video_id, languages=[chosen.language_code])
                lang_code = chosen.language_code
        except TranscriptsDisabled:
            return {"transcript": None, "note": "TRANSCRIPT_DISABLED"}
        except NoTranscriptFound:
            return {"transcript": None, "note": "TRANSCRIPT_NOT_FOUND"}
        except Exception:
            # Nếu list() thất bại, thử fetch() không tham số (lấy default)
            try:
                result = api.fetch(video_id)
                lang_code = getattr(result, "language_code", None)
            except TranscriptsDisabled:
                return {"transcript": None, "note": "TRANSCRIPT_DISABLED"}
            except NoTranscriptFound:
                return {"transcript": None, "note": "TRANSCRIPT_NOT_FOUND"}
            except Exception:
                return {"transcript": None, "note": "TRANSCRIPT_ERROR"}

    if result is None:
        return {"transcript": None, "note": "TRANSCRIPT_NOT_FOUND"}

    # Ghép text — snippet là FetchedTranscriptSnippet với thuộc tính .text
    def _get_text(snip: Any) -> str:
        if hasattr(snip, "text"):
            return snip.text or ""
        if isinstance(snip, dict):
            return snip.get("text", "")
        return ""

    full_text = " ".join(_get_text(snip) for snip in result).strip()

    return {
        "transcript": full_text[:MAX_TRANSCRIPT_CHARS],
        "transcript_length": len(full_text),
        "language": lang_code or getattr(result, "language_code", None),
        "is_auto_generated": getattr(result, "is_generated", False),
        "note": None,
    }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

async def extract_youtube_video(url: str) -> Dict[str, Any]:
    """FR3.3: YouTube — transcript + oEmbed metadata, chạy song song.

    Raises RuntimeError("INVALID_YOUTUBE_URL") nếu không bóc được video ID.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise RuntimeError("INVALID_YOUTUBE_URL")

    loop = asyncio.get_running_loop()
    metadata_task = asyncio.create_task(_fetch_oembed(url, "youtube.com"))
    transcript_result = await loop.run_in_executor(
        None, _fetch_transcript_sync, video_id
    )
    metadata = await metadata_task or {}

    return {
        "url": url,
        "platform": "YouTube",
        "video_id": video_id,
        "title": metadata.get("title", ""),
        "channel": metadata.get("channel", ""),
        "thumbnail_url": metadata.get("thumbnail_url", ""),
        "description": "",
        "transcript": transcript_result.get("transcript"),
        "transcript_length": transcript_result.get("transcript_length", 0),
        "transcript_language": transcript_result.get("language"),
        "is_auto_generated": transcript_result.get("is_auto_generated"),
        "note": transcript_result.get("note"),
    }


async def extract_generic_video(url: str) -> Dict[str, Any]:
    """FR3.3: mọi nền tảng video KHÔNG phải YouTube.

    Thứ tự: oEmbed → OG HTML fallback.
    Không có transcript — trả note=TRANSCRIPT_NOT_AVAILABLE.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    platform = _detect_platform(hostname)

    # Thử oEmbed trước (nhanh, không cần parse HTML)
    metadata = await _fetch_oembed(url, hostname)

    # Fallback: fetch HTML + OG tags
    if not metadata or not metadata.get("title"):
        metadata = await _fetch_og_metadata(url)

    # Nếu vẫn không có title (file .mp4, link hỏng...) → lấy từ tên file
    title = metadata.get("title", "")
    if not title:
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            title = path_parts[-1].rsplit(".", 1)[0].replace("-", " ").replace("_", " ")

    return {
        "url": url,
        "platform": platform,
        "video_id": None,
        "title": title,
        "channel": metadata.get("channel", ""),
        "thumbnail_url": metadata.get("thumbnail_url", ""),
        "description": (metadata.get("description", "") or "")[:MAX_DESCRIPTION_CHARS],
        "transcript": None,
        "transcript_length": 0,
        "transcript_language": None,
        "is_auto_generated": False,
        "note": "TRANSCRIPT_NOT_AVAILABLE",
    }


async def extract_video_info(url: str) -> Dict[str, Any]:
    """FR3.3: smart router — YouTube → transcript, còn lại → metadata.

    Entry point duy nhất mà dispatcher gọi.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if _is_youtube(hostname):
        return await extract_youtube_video(url)
    return await extract_generic_video(url)
