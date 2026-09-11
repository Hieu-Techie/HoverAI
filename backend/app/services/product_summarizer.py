"""Module 3, FR3.2: tóm tắt trang sản phẩm bằng Gemini, kèm tên sản phẩm chuẩn hóa tiếng Việt."""

import os
from typing import Any, Dict, Optional

from app.services.gemini_client import GEMINI_MODEL, call_gemini_async  # noqa: F401

SUMMARY_MAX_INPUT_CHARS = 30_000

# Marker tách tên sản phẩm và tóm tắt trong response Gemini
_NAME_MARKER = "TÊN SẢN PHẨM:"


def build_product_summary_prompt(product: Dict[str, Any]) -> str:
    """FR3.2: prompt yêu cầu Gemini chuẩn hóa tên sản phẩm và tóm tắt 3 ý khách quan.

    Quy tắc tên:
    - Giữ nguyên tên thương hiệu và mã model (Sony, WH-1000XM5, iPhone 16 Pro).
    - Nếu có phần mô tả tiếng Anh kèm tên → dịch phần mô tả sang tiếng Việt.
    - Nếu tên đã là tiếng Việt tự nhiên → giữ nguyên.
    """
    name = product.get("name") or "Sản phẩm"
    price = product.get("price_display") or product.get("price") or "Không rõ"
    rating = product.get("rating_display") or product.get("rating") or "Không rõ"
    brand = product.get("brand") or "Không rõ"
    description = (product.get("description") or "")[:SUMMARY_MAX_INPUT_CHARS]

    return f"""Bạn là trợ lý tóm tắt thông tin sản phẩm khách quan, viết bằng tiếng Việt.

NHIỆM VỤ: Hãy đọc thông tin sản phẩm dưới đây và trả về đúng 4 dòng theo định dạng sau. TUYỆT ĐỐI KHÔNG thêm bất kỳ text nào khác.

TÊN SẢN PHẨM: <tên sản phẩm bằng tiếng Việt — giữ nguyên tên thương hiệu & mã model (Sony, iPhone, WH-1000XM5...), dịch phần mô tả tiếng Anh nếu có, giữ nguyên nếu tên đã là tiếng Việt tự nhiên>
- <điểm nổi bật chính: tính năng hoặc công dụng chính>
- <thông tin giá và đánh giá từ người dùng (nếu có dữ liệu)>
- <điều người mua nên biết hoặc lưu ý trước khi mua>

QUY TẮC:
- Mỗi ý là một câu ngắn gọn, khách quan, chỉ dựa trên dữ liệu được cung cấp.
- BẮT BUỘC bắt đầu mỗi ý bằng ký tự "-" (dấu gạch ngang) rồi khoảng trắng.
- Tuyệt đối KHÔNG dùng dấu "*", KHÔNG có câu mở đầu hay kết luận.
- Nếu không có thông tin giá/đánh giá thì ghi: "Chưa có thông tin giá/đánh giá."

Tên sản phẩm gốc: {name}
Thương hiệu: {brand}
Giá: {price}
Đánh giá: {rating}

Mô tả:
{description}
"""


def _parse_product_result(raw: str) -> Dict[str, Optional[str]]:
    """Tách tên sản phẩm đã chuẩn hóa và phần tóm tắt từ response Gemini."""
    raw = (raw or "").strip()
    name_vi: Optional[str] = None
    summary_lines = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not name_vi and stripped.upper().startswith(_NAME_MARKER.upper()):
            candidate = stripped[len(_NAME_MARKER):].strip()
            if candidate:
                name_vi = candidate
        elif stripped.startswith("-"):
            summary_lines.append(stripped)

    summary = "\n".join(summary_lines) if summary_lines else (raw if not name_vi else None)
    return {"name_vi": name_vi, "summary": summary}


async def summarize_product(
    product: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Optional[str]]]:
    """FR3.2: gọi Gemini qua gemini_client (thread-safe BYOK); trả dict {name_vi, summary}.

    name_vi: tên sản phẩm đã chuẩn hóa tiếng Việt (giữ brand/model, dịch mô tả)
    summary: tóm tắt 3 gạch đầu dòng tiếng Việt
    """
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key or (not product.get("name") and not product.get("description")):
        return None

    prompt = build_product_summary_prompt(product)
    raw = await call_gemini_async(key, prompt)
    return _parse_product_result(raw) if raw else None
