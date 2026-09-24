"""FR3.3: Gemini summarization cho video từ mọi nền tảng.

Prompt ưu tiên:
1. Có transcript (YouTube)   → tóm tắt từ nội dung thực
2. Có description (Vimeo...) → tóm tắt từ mô tả video
3. Chỉ có title              → dự đoán từ tiêu đề

Output chuẩn:
    TÊN VIDEO: <tiêu đề tiếng Việt>
    - <điểm chính 1>
    - <điểm chính 2>
    - <điểm chính 3>
"""

import os
from typing import Any, Dict, Optional

from app.services.core.gemini_client import call_gemini_async

# Số ký tự tối đa của transcript gửi cho Gemini
TRANSCRIPT_PROMPT_MAX_CHARS = 10_000
DESCRIPTION_PROMPT_MAX_CHARS = 2_500


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_video_summary_prompt(
    title: str,
    transcript: str,
    channel: str = "",
    is_auto_generated: bool = False,
    platform: str = "YouTube",
) -> str:
    """Prompt khi có transcript đầy đủ."""
    channel_line = f"Kênh: {channel}\n" if channel else ""
    auto_note = " (phụ đề tự động — có thể có lỗi)" if is_auto_generated else ""
    trimmed = transcript[:TRANSCRIPT_PROMPT_MAX_CHARS]

    return (
        f"Bạn là trợ lý phân tích video {platform} chuyên nghiệp phục vụ người Việt Nam.\n\n"
        f"Tiêu đề video: {title}\n"
        f"{channel_line}"
        f"Transcript{auto_note}:\n{trimmed}\n\n"
        "Nhiệm vụ:\n"
        "1. Xác nhận hoặc chuẩn hóa tên video sang tiếng Việt tự nhiên nếu cần "
        "(giữ nguyên nếu tiêu đề đã chuẩn).\n"
        "2. Tóm tắt nội dung video thành ĐÚNG 3 điểm chính, khách quan, bằng tiếng Việt.\n\n"
        "Định dạng trả lời CHÍNH XÁC (không thêm bất cứ nội dung nào khác):\n"
        "TÊN VIDEO: <tiêu đề tiếng Việt>\n"
        "- <điểm chính 1>\n"
        "- <điểm chính 2>\n"
        "- <điểm chính 3>"
    )


def build_video_description_prompt(
    title: str,
    description: str,
    channel: str = "",
    platform: str = "video",
) -> str:
    """Prompt khi có description nhưng không có transcript (Vimeo, TikTok, v.v.)."""
    channel_line = f"Kênh: {channel}\n" if channel else ""
    trimmed = description[:DESCRIPTION_PROMPT_MAX_CHARS]

    return (
        f"Bạn là trợ lý phân tích video phục vụ người Việt Nam.\n\n"
        f"Nền tảng: {platform}\n"
        f"Tiêu đề: {title}\n"
        f"{channel_line}"
        f"Mô tả video:\n{trimmed}\n\n"
        "Video này không có transcript trực tiếp. Hãy dựa vào tiêu đề và mô tả để:\n"
        "1. Chuẩn hóa tên video sang tiếng Việt nếu cần.\n"
        "2. Tóm tắt nội dung chính thành 3 điểm (dựa trên mô tả thực, không phải dự đoán).\n\n"
        "Định dạng CHÍNH XÁC:\n"
        "TÊN VIDEO: <tiêu đề tiếng Việt>\n"
        "- <điểm chính 1>\n"
        "- <điểm chính 2>\n"
        "- <điểm chính 3>"
    )


def build_video_metadata_only_prompt(
    title: str,
    channel: str = "",
    platform: str = "video",
) -> str:
    """Fallback — chỉ có tiêu đề, không có transcript hay description."""
    channel_line = f"Kênh: {channel}\n" if channel else ""
    return (
        f"Bạn là trợ lý phân tích video phục vụ người Việt Nam.\n\n"
        f"Nền tảng: {platform}\n"
        f"Tiêu đề: {title}\n"
        f"{channel_line}"
        "Video này không có phụ đề hay mô tả. Hãy dựa vào tiêu đề để:\n"
        "1. Chuẩn hóa tên video sang tiếng Việt nếu cần.\n"
        "2. DỰ ĐOÁN nội dung thành 3 điểm (ghi rõ đây là dự đoán).\n\n"
        "Định dạng CHÍNH XÁC:\n"
        "TÊN VIDEO: <tiêu đề tiếng Việt>\n"
        "- <dự đoán 1>\n"
        "- <dự đoán 2>\n"
        "- <dự đoán 3>"
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_video_result(raw: str) -> Dict[str, Optional[str]]:
    """Phân tích response Gemini → {title_vi, summary}."""
    if not raw:
        return {"title_vi": None, "summary": None}

    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    title_vi: Optional[str] = None
    bullets = []

    for line in lines:
        upper_line = line.upper()
        if upper_line.startswith("TÊN VIDEO:") or upper_line.startswith("TEN VIDEO:"):
            title_vi = line.split(":", 1)[-1].strip() or None
        elif line.startswith("- "):
            bullets.append(line)

    summary = "\n".join(bullets) if bullets else None
    return {"title_vi": title_vi, "summary": summary}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def summarize_video(
    title: str,
    transcript: Optional[str] = None,
    description: Optional[str] = None,
    channel: str = "",
    is_auto_generated: bool = False,
    platform: str = "video",
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """FR3.3: gọi Gemini tóm tắt nội dung video — mọi nền tảng.

    Ưu tiên: transcript > description > title-only.
    Trả None nếu không có API key hoặc không có dữ liệu gì.
    """
    # Fallback sang env var nếu extension không gửi key (giống summarize_article)
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None

    if transcript:
        prompt = build_video_summary_prompt(
            title, transcript, channel, is_auto_generated, platform
        )
    elif description and len(description.strip()) > 30:
        prompt = build_video_description_prompt(title, description, channel, platform)
    elif title:
        prompt = build_video_metadata_only_prompt(title, channel, platform)
    else:
        return None

    raw = await call_gemini_async(key, prompt)
    if not raw:
        return None

    return _parse_video_result(raw)

