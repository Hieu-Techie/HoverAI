"""Module 3, FR3.1: tóm tắt bài viết bằng Gemini, kèm tiêu đề chuẩn hóa tiếng Việt."""

import os
from typing import Dict, Optional

from app.services.gemini_client import GEMINI_MODEL, call_gemini_async  # noqa: F401

SUMMARY_MAX_INPUT_CHARS = 30_000

# Marker dùng để tách tiêu đề và tóm tắt trong response của Gemini
_TITLE_MARKER = "TIÊU ĐỀ:"


def build_article_summary_prompt(title: str, text: str) -> str:
    """FR3.1: prompt yêu cầu Gemini chuẩn hóa tiêu đề và tóm tắt 3 ý chính.

    Nếu tiêu đề gốc đã là tiếng Việt tự nhiên → giữ nguyên.
    Nếu tiêu đề bằng tiếng Anh / không tự nhiên → dịch/viết lại súc tích tiếng Việt.
    """
    article_text = text[:SUMMARY_MAX_INPUT_CHARS]
    return f"""Bạn là trợ lý tóm tắt và biên tập nội dung tiếng Việt.

NHIỆM VỤ: Hãy đọc bài viết dưới đây và trả về đúng 4 dòng theo định dạng sau. TUYỆT ĐỐI KHÔNG thêm bất kỳ text nào khác, không có lời chào, không có câu giải thích.

TIÊU ĐỀ: <tiêu đề bài viết bằng tiếng Việt — nếu tiêu đề gốc đã là tiếng Việt tự nhiên thì giữ nguyên, nếu bằng tiếng Anh hoặc không tự nhiên thì dịch/viết lại súc tích bằng tiếng Việt>
- <ý chính thứ nhất dựa trên nội dung bài>
- <ý chính thứ hai dựa trên nội dung bài>
- <ý chính thứ ba dựa trên nội dung bài>

QUY TẮC:
- Mỗi ý chính là một câu ngắn gọn, khách quan, không suy đoán ngoài bài.
- BẮT BUỘC bắt đầu mỗi ý bằng ký tự "-" (dấu gạch ngang) rồi khoảng trắng.
- Tuyệt đối KHÔNG dùng dấu "*", KHÔNG có câu mở đầu như "Dưới đây là...".
- Tiêu đề giữ tên thương hiệu/riêng trong ngoặc nếu cần (VD: "Apple ra mắt iPhone 17").

Tiêu đề gốc: {title}

Nội dung bài viết:
{article_text}
"""


def _parse_article_result(raw: str) -> Dict[str, Optional[str]]:
    """Tách tiêu đề đã chuẩn hóa và phần tóm tắt từ response Gemini."""
    raw = (raw or "").strip()
    title_vi: Optional[str] = None
    summary_lines = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not title_vi and stripped.upper().startswith(_TITLE_MARKER.upper()):
            candidate = stripped[len(_TITLE_MARKER):].strip()
            if candidate:
                title_vi = candidate
        elif stripped.startswith("-"):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else (raw if not title_vi else None)
    return {"title_vi": title_vi, "summary": summary}


async def summarize_article(
    title: str,
    text: str,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Optional[str]]]:
    """FR3.1: gọi Gemini qua gemini_client (thread-safe BYOK); trả dict {title_vi, summary}.

    title_vi: tiêu đề đã chuẩn hóa sang tiếng Việt (hoặc None nếu không parse được)
    summary:  tóm tắt 3 gạch đầu dòng tiếng Việt
    """
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key or not text.strip():
        return None

    prompt = build_article_summary_prompt(title, text)
    raw = await call_gemini_async(key, prompt)
    return _parse_article_result(raw) if raw else None
