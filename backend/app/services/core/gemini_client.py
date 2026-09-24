"""Shared Gemini AI client — thread-safe, per-request client instantiation (BYOK-safe).

VẤN ĐỀ VỚI SDK CŨ (google-generativeai):
  genai.configure(api_key=...) thiết lập GLOBAL state — không an toàn khi nhiều
  request đồng thời dùng các API key khác nhau (BYOK). Thread A có thể ghi đè
  key của Thread B giữa chừng.

GIẢI PHÁP VỚI SDK MỚI (google-genai):
  Khởi tạo genai.Client(api_key=...) riêng cho từng request. Client này
  hoàn toàn độc lập, không chia sẻ state với các request khác.

Usage (các summarizer gọi qua đây, không dùng genai.configure trực tiếp):
    raw = await call_gemini_async(api_key, prompt)
"""

import asyncio
import os
from typing import Optional

from google import genai

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_SECONDS = 20


def call_gemini_sync(api_key: str, prompt: str) -> str:
    """Blocking Gemini call — an toàn để chạy trong ThreadPoolExecutor.

    Mỗi lần gọi tạo một Client riêng với API key riêng — các request
    BYOK dùng key khác nhau KHÔNG bao giờ ảnh hưởng lẫn nhau.
    """
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


async def call_gemini_async(
    api_key: str,
    prompt: str,
    timeout: int = GEMINI_TIMEOUT_SECONDS,
) -> Optional[str]:
    """Async wrapper không chặn event loop.

    Returns:
        Chuỗi kết quả từ Gemini, hoặc None nếu timeout/lỗi bất kỳ.
    """
    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, call_gemini_sync, api_key, prompt),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, Exception):
        return None

