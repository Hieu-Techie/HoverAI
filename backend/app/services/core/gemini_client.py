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

# Model mặc định (đọc từ .env, fallback sang gemini-3.5-flash-lite nếu không có)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TIMEOUT_SECONDS = 20

# Chuỗi fallback (đã test thực tế với key trong .env, tháng 10/2026):
# gemini-2.5-flash bị 429 (20 req/day free tier)
# gemini-3.5-flash-lite và gemini-3.5-flash đều hoạt động tốt.
_FALLBACK_CHAIN = [
    "gemini-3.5-flash-lite",  # nhanh, ít tốn quota — ưu tiên đầu tiên
    "gemini-3.5-flash",       # mạnh hơn, fallback thứ 2
]


def call_gemini_sync(api_key: str, prompt: str, model: Optional[str] = None) -> str:
    """Blocking Gemini call — an toàn để chạy trong ThreadPoolExecutor.

    Tự động fallback qua _FALLBACK_CHAIN nếu gặp 429 (quota) hoặc 404 (model không tồn tại).
    Mỗi lần gọi tạo một Client riêng với API key riêng — các request
    BYOK dùng key khác nhau KHÔNG bao giờ ảnh hưởng lẫn nhau.
    """
    client = genai.Client(api_key=api_key)

    # Xây dựng chuỗi thử: bắt đầu từ model yêu cầu, rồi các model fallback
    start_model = model or GEMINI_MODEL
    chain = [start_model] + [m for m in _FALLBACK_CHAIN if m != start_model]

    last_error = None
    for attempt_model in chain:
        try:
            response = client.models.generate_content(
                model=attempt_model,
                contents=prompt,
            )
            return (response.text or "").strip()
        except Exception as e:
            err_str = str(e)
            # Chỉ fallback khi gặp quota (429), model không còn tồn tại (404), hoặc quá tải (503)
            if "429" in err_str or "404" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                last_error = e
                continue
            # Lỗi khác (401 key sai, network, v.v.) → raise ngay
            raise

    # Hết chuỗi fallback → raise lỗi cuối
    raise RuntimeError(f"Tất cả Gemini models đều thất bại. Lỗi cuối: {last_error}") from last_error


async def call_gemini_async(
    api_key: str,
    prompt: str,
    timeout: int = GEMINI_TIMEOUT_SECONDS,
    model: Optional[str] = None,
) -> Optional[str]:
    """Async wrapper không chặn event loop.

    Returns:
        Chuỗi kết quả từ Gemini, hoặc None nếu timeout/lỗi không phục hồi được.
    """
    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, call_gemini_sync, api_key, prompt, model),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None
