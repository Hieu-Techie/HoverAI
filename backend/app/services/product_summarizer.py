"""Module 3, FR3.2: tóm tắt trang sản phẩm bằng Gemini với prompt chuyên biệt."""

import asyncio
import os
from typing import Any, Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SUMMARY_MAX_INPUT_CHARS = 30_000
SUMMARY_TIMEOUT_SECONDS = 20


def build_product_summary_prompt(product: Dict[str, Any]) -> str:
    """FR3.2: prompt yêu cầu Gemini tóm tắt sản phẩm theo 3 ý khách quan."""
    name = product.get("name") or "Sản phẩm"
    price = product.get("price_display") or product.get("price") or "Không rõ"
    rating = product.get("rating_display") or product.get("rating") or "Không rõ"
    brand = product.get("brand") or "Không rõ"
    description = (product.get("description") or "")[:SUMMARY_MAX_INPUT_CHARS]

    return f"""Bạn là trợ lý tóm tắt thông tin sản phẩm khách quan.
YÊU CẦU ĐỊNH DẠNG NGHIÊM NGẶT BẮT BUỘC:
1. Tóm tắt thông tin sản phẩm dưới đây thành đúng 3 gạch đầu dòng bằng tiếng Việt. Tuyệt đối KHÔNG có câu mở đầu hay câu kết luận.
2. Gạch đầu dòng 1: điểm nổi bật chính của sản phẩm (tính năng, công dụng chính).
3. Gạch đầu dòng 2: thông tin giá và đánh giá từ người dùng (nếu có).
4. Gạch đầu dòng 3: điều người mua nên biết hoặc lưu ý trước khi mua.
5. BẮT BUỘC bắt đầu mỗi dòng bằng ký tự "-" (dấu gạch ngang) theo sau là khoảng trắng. Tuyệt đối KHÔNG dùng dấu "*".
6. Không suy đoán, không thêm thông tin ngoài dữ liệu được cung cấp.

Tên sản phẩm: {name}
Thương hiệu: {brand}
Giá: {price}
Đánh giá: {rating}

Mô tả:
{description}
"""


def _generate_product_summary(api_key: str, product: Dict[str, Any]) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(build_product_summary_prompt(product))
    return (response.text or "").strip()


async def summarize_product(
    product: Dict[str, Any], api_key: Optional[str] = None
) -> Optional[str]:
    """FR3.2: gọi Gemini tóm tắt sản phẩm, không chặn event loop; lỗi trả None."""
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    # Cần ít nhất tên hoặc mô tả để tóm tắt.
    if not key or (not product.get("name") and not product.get("description")):
        return None
    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _generate_product_summary, key, product),
            timeout=SUMMARY_TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, Exception):
        return None

