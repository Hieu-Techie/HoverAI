"""Module 3, FR3.1: tạo bản tóm tắt bài viết bằng Gemini."""

import asyncio
import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SUMMARY_MAX_INPUT_CHARS = 30000
SUMMARY_TIMEOUT_SECONDS = 20


def build_article_summary_prompt(title: str, text: str) -> str:
    """FR3.1: prompt chuẩn yêu cầu đúng 3 ý chính, khách quan và không bịa thêm."""
    article_text = text[:SUMMARY_MAX_INPUT_CHARS]
    return f"""Bạn là trợ lý tóm tắt văn bản khách quan.
YÊU CẦU ĐỊNH DẠNG NGHIÊM NGẶT BẮT BUỘC:
1. Hãy tóm tắt bài viết dưới đây thành đúng 3 gạch đầu dòng bằng tiếng Việt. Tuyệt đối KHÔNG có câu mở đầu (như "Dưới đây là...", "Tóm tắt:"). Tuyệt đối KHÔNG có câu kết luận hay chào hỏi.
2. Mỗi gạch đầu dòng chỉ nêu một ý chính dựa trên nội dung được cung cấp.
3. BẮT BUỘC bắt đầu mỗi dòng bằng ký tự "-" (dấu gạch ngang) theo sau là khoảng trắng. Tuyệt đối KHÔNG dùng dấu "*".
4. Không suy đoán, không thêm thông tin ngoài bài viết và không dùng tiêu đề quảng cáo.

Tiêu đề: {title}

Nội dung:
{article_text}
"""


def _generate_summary(api_key: str, title: str, text: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(build_article_summary_prompt(title, text))
    return (response.text or "").strip()


async def summarize_article(
    title: str, text: str, api_key: Optional[str] = None
) -> Optional[str]:
    """FR3.1: gọi Gemini không chặn event loop; thiếu key/lỗi thì trả None."""
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key or not text.strip():
        return None

    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _generate_summary, key, title, text),
            timeout=SUMMARY_TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, Exception):
        return None
