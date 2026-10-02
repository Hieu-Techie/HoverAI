"""FR3.5: Deep Scan Audio — endpoint tải và phân tích audio video bằng Gemini."""

import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException
from app.models.video import DeepScanRequest, DeepScanResponse
from typing import Optional

from app.services.extractors.audio_extractor import download_video_audio, cleanup_audio_tmpdir

logger = logging.getLogger(__name__)
router = APIRouter()

DEEPSCAN_TOTAL_TIMEOUT_S = 180  # 3 phút (download + upload + analyze)


@router.post("/api/deepscan-audio", response_model=DeepScanResponse)
async def deepscan_audio(request: DeepScanRequest):
    """FR3.5: tải audio + phân tích chi tiết bằng Gemini Files API.

    Pipeline:
      1. yt-dlp tải audio-only stream (max 5 phút)
      2. Upload lên Gemini Files API
      3. Gemini phân tích → trích xuất mốc thời gian + key points
      4. Cleanup file tạm

    Thời gian xử lý: 30–90 giây tùy video.
    """
    from app.services.summarizers.audio_analyzer import analyze_audio  # local import

    # Resolve API key (BYOK → env var fallback)
    api_key = request.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY_REQUIRED: cần cấu hình API key để dùng Deep Scan",
        )

    url = str(request.url)
    audio_path: Optional[str] = None
    tmpdir: Optional[str] = None

    try:
        # Bước 1: tải audio (dùng cookie của user nếu có để bypass bot detection)
        logger.info("FR3.5: bắt đầu Deep Scan cho %s", url)
        cookie_header = request.yt_cookie_header or ""
        if cookie_header:
            logger.info("FR3.5: sử dụng cookie từ extension (%d chars)", len(cookie_header))
        audio_path, info = await asyncio.wait_for(
            download_video_audio(url, cookie_header=cookie_header),
            timeout=120,  # 2 phút để tải
        )
        tmpdir = os.path.dirname(audio_path)


        # Bước 2: phân tích bằng Gemini
        result = await analyze_audio(
            audio_path=audio_path,
            title=info.get("title", ""),
            duration=info.get("duration", 0),
            platform=info.get("platform", "Video"),
            api_key=api_key,
        )

        logger.info("FR3.5: Deep Scan hoàn thành cho %s", url)

        return {
            "url": url,
            "title": info.get("title", ""),
            "title_vi": result.get("title_vi"),
            "summary": result.get("summary"),
            "key_points": result.get("key_points"),
            "duration": info.get("duration"),
            "channel": info.get("channel"),
            "platform": info.get("platform"),
            "is_deep_scan": True,
        }

    except asyncio.TimeoutError:
        logger.warning("FR3.5: timeout khi xử lý %s", url)
        raise HTTPException(
            status_code=504,
            detail="DEEPSCAN_TIMEOUT: quá thời gian xử lý (max 3 phút). Video có thể quá dài.",
        )
    except RuntimeError as exc:
        code = str(exc).split(":")[0]
        logger.error("FR3.5: lỗi runtime %s — %s", code, url)
        _error_map = {
            "AUDIO_INFO_FAILED": (502, "Không thể lấy thông tin video. Kiểm tra URL và thử lại."),
            "AUDIO_DOWNLOAD_FAILED": (502, "Không thể tải audio từ video này. URL có thể bị giới hạn."),
            "AUDIO_FILE_TOO_LARGE": (413, "File audio quá lớn (>50MB). Thử với video ngắn hơn."),
            "AUDIO_FILE_PROCESSING_FAILED": (502, "Gemini không xử lý được file audio này."),
            "GEMINI_API_KEY_REQUIRED": (400, "Cần API key để dùng Deep Scan."),
        }
        msg = _error_map.get(code, (500, f"Deep Scan lỗi: {exc}"))
        raise HTTPException(status_code=msg[0], detail=msg[1]) from exc
    except Exception as exc:
        err_str = str(exc)
        # 429 Quota exceeded — thông báo rõ ràng thay vì DEEPSCAN_ERROR generic
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            logger.warning("FR3.5: Gemini quota exhausted — %s", url)
            raise HTTPException(
                status_code=429,
                detail="GEMINI_QUOTA_EXCEEDED: Đã vượt giới hạn miễn phí của Gemini API hôm nay (20 lần/ngày). Thử lại vào ngày mai hoặc nâng cấp API key.",
            ) from exc
        logger.error("FR3.5: lỗi không dự kiến: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"DEEPSCAN_ERROR: {exc}"
        ) from exc

    finally:
        # Cleanup file tạm dù thành công hay lỗi
        if tmpdir:
            cleanup_audio_tmpdir(tmpdir)
            logger.info("FR3.5: đã dọn dẹp thư mục tạm %s", tmpdir)

