"""FR3.5: phân tích audio bằng Gemini Files API.

Pipeline:
  1. Upload file audio lên Gemini Files API
  2. Chờ file ở trạng thái ACTIVE
  3. Gửi prompt phân tích (tiêu đề chuẩn hóa + tóm tắt + key points có timestamp)
  4. Parse kết quả
  5. Xóa file khỏi Gemini (cleanup)

Gemini Files API hỗ trợ audio: mp3, mp4, aac, ogg, flac, wav, webm, m4a, v.v.
Giới hạn: 2 GB / file, tối đa 50 file tồn tại cùng lúc.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

from google import genai

from app.services.core.gemini_client import GEMINI_MODEL

logger = logging.getLogger(__name__)

UPLOAD_WAIT_TIMEOUT_S = 60    # Tối đa chờ file ACTIVE
ANALYSIS_TIMEOUT_S = 120      # Tối đa phân tích

# Mapping phần mở rộng file → MIME type cho Gemini Files API
_MIME_MAP = {
    ".m4a":  "audio/mp4",
    ".mp4":  "audio/mp4",
    ".webm": "audio/webm",
    ".mp3":  "audio/mpeg",
    ".ogg":  "audio/ogg",
    ".flac": "audio/flac",
    ".wav":  "audio/wav",
    ".aac":  "audio/aac",
}


def _build_analysis_prompt(title: str, duration: int, platform: str) -> str:
    """FR3.5: prompt phân tích audio với timestamp."""
    mins = duration // 60
    secs = duration % 60
    duration_str = f"{mins}:{secs:02d}" if mins else f"{secs}s"

    return f"""Bạn là trợ lý phân tích nội dung video/audio, phục vụ người Việt Nam.

Video: "{title}" ({platform}, ~{duration_str})

NHIỆM VỤ: Nghe audio và trả về đúng định dạng sau. TUYỆT ĐỐI KHÔNG thêm bất kỳ nội dung nào khác.

TÊN VIDEO: <tiêu đề đã chuẩn hóa tiếng Việt — giữ tên riêng/thương hiệu, dịch phần Anh nếu có>
TÓM TẮT: <tóm tắt nội dung chính 2-3 câu tiếng Việt>
ĐIỂM CHÍNH:
- [m:ss] <nội dung điểm chính 1 với mốc thời gian>
- [m:ss] <nội dung điểm chính 2>
- [m:ss] <nội dung điểm chính 3>
- [m:ss] <nội dung điểm chính 4 nếu có>
- [m:ss] <nội dung điểm chính 5 nếu có>

QUY TẮC:
- Mốc thời gian [m:ss] là bắt buộc nếu audio có thể xác định vị trí.
- Mỗi điểm chính là 1 câu ngắn gọn, khách quan.
- Nếu nội dung bằng tiếng nước ngoài → dịch sang tiếng Việt.
- Tuyệt đối KHÔNG dùng dấu "*" hay markdown khác.
"""


def _parse_audio_analysis(raw: str) -> Dict[str, Any]:
    """Tách TÊN VIDEO, TÓM TẮT và ĐIỂM CHÍNH từ response Gemini."""
    lines = [l.strip() for l in (raw or "").strip().splitlines() if l.strip()]

    title_vi: Optional[str] = None
    summary: Optional[str] = None
    key_points: list = []
    in_points = False

    for line in lines:
        upper = line.upper()
        if upper.startswith("TÊN VIDEO:") or upper.startswith("TEN VIDEO:"):
            title_vi = line.split(":", 1)[-1].strip() or None
            in_points = False
        elif upper.startswith("TÓM TẮT:") or upper.startswith("TOM TAT:"):
            summary = line.split(":", 1)[-1].strip() or None
            in_points = False
        elif upper.startswith("ĐIỂM CHÍNH") or upper.startswith("DIEM CHINH"):
            in_points = True
        elif in_points and line.startswith("-"):
            key_points.append(line)

    return {
        "title_vi": title_vi,
        "summary": summary,
        "key_points": "\n".join(key_points) if key_points else None,
    }


def _extract_retry_delay(exc: Exception) -> int:
    """Trích xuất số giây retry từ thông báo lỗi 429 của Gemini."""
    import re
    msg = str(exc)
    m = re.search(r'retry[^\d]*(\d+)', msg, re.IGNORECASE)
    return int(m.group(1)) + 2 if m else 45  # +2 giây buffer


def _generate_with_fallback(
    client: Any, model: str, contents: list, fallback_model: str = "gemini-3.5-flash-lite"
) -> str:
    """Gọi Gemini generate_content với retry 1 lần nếu 429.

    Thứ tự:
    1. Thử model chính (GEMINI_MODEL, mặc định gemini-2.5-flash)
    2. Nếu 429 → chờ retry_delay giây → thử lại với fallback_model
    3. Nếu vẫn 429 → raise để caller xử lý
    """
    try:
        response = client.models.generate_content(model=model, contents=contents)
        return (response.text or "").strip()
    except Exception as exc:
        err_str = str(exc)
        if "429" not in err_str and "RESOURCE_EXHAUSTED" not in err_str:
            raise  # Lỗi khác → không retry

        # 429: chờ rồi thử fallback model
        delay = _extract_retry_delay(exc)
        logger.warning(
            "FR3.5: Gemini 429 trên %s — chờ %ds rồi thử %s", model, delay, fallback_model
        )
        time.sleep(delay)
        response = client.models.generate_content(model=fallback_model, contents=contents)
        return (response.text or "").strip()


def _analyze_audio_sync(
    audio_path: str, title: str, duration: int, platform: str, api_key: str
) -> Dict[str, Any]:
    """Đồng bộ: upload + phân tích bằng Gemini Files API."""
    client = genai.Client(api_key=api_key)

    ext = os.path.splitext(audio_path)[1].lower()
    mime_type = _MIME_MAP.get(ext, "audio/mpeg")

    # --- Upload ---
    logger.info("FR3.5: đang upload audio lên Gemini Files API (%s, %s)…", ext, mime_type)
    file_ref = client.files.upload(
        file=audio_path,
        config={"mime_type": mime_type, "display_name": "hoverai_audio"},
    )

    # --- Chờ ACTIVE ---
    waited = 0
    while waited < UPLOAD_WAIT_TIMEOUT_S:
        state_name = getattr(getattr(file_ref, "state", None), "name", None) or ""
        if state_name != "PROCESSING":
            break
        time.sleep(2)
        waited += 2
        try:
            file_ref = client.files.get(name=file_ref.name)
        except Exception:
            break

    state_final = getattr(getattr(file_ref, "state", None), "name", "UNKNOWN")
    if state_final == "FAILED":
        client.files.delete(name=file_ref.name)
        raise RuntimeError("AUDIO_FILE_PROCESSING_FAILED")

    logger.info("FR3.5: file ở trạng thái %s sau %ds", state_final, waited)

    # --- Phân tích (với retry 429) ---
    prompt = _build_analysis_prompt(title, duration, platform)
    try:
        raw = _generate_with_fallback(
            client=client,
            model=GEMINI_MODEL,
            contents=[file_ref, prompt],
        )
    finally:
        # Cleanup file khỏi Gemini dù thành công hay lỗi
        try:
            client.files.delete(name=file_ref.name)
            logger.info("FR3.5: đã xóa file khỏi Gemini Files API")
        except Exception as del_err:
            logger.warning("FR3.5: không xóa được file Gemini: %s", del_err)

    return _parse_audio_analysis(raw)



async def analyze_audio(
    audio_path: str,
    title: str,
    duration: int,
    platform: str,
    api_key: str,
) -> Dict[str, Any]:
    """Async wrapper: phân tích audio bằng Gemini.

    Raises:
        asyncio.TimeoutError nếu vượt ANALYSIS_TIMEOUT_S
        RuntimeError với mã: AUDIO_FILE_PROCESSING_FAILED
    """
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(
            None, _analyze_audio_sync, audio_path, title, duration, platform, api_key
        ),
        timeout=ANALYSIS_TIMEOUT_S,
    )

