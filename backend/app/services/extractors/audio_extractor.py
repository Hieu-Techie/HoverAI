"""FR3.5: tải audio từ YouTube/các nền tảng video bằng yt-dlp.

Hỗ trợ: YouTube, Vimeo, Facebook Video, TikTok, và các nền tảng yt-dlp biết.
Giới hạn: tối đa MAX_AUDIO_SECONDS giây đầu (nếu ffmpeg khả dụng) hoặc
           từ chối nếu file > MAX_FILE_SIZE_MB MB.
"""

import asyncio
import logging
import os
import tempfile
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

MAX_AUDIO_SECONDS = 300        # 5 phút — giới hạn deep scan
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def cleanup_audio_tmpdir(tmpdir: str) -> None:
    """Xóa thư mục tạm sau khi phân tích audio (không raise nếu thất bại)."""
    try:
        for f in os.listdir(tmpdir):
            try:
                os.unlink(os.path.join(tmpdir, f))
            except OSError:
                pass
        os.rmdir(tmpdir)
    except OSError:
        pass


def _download_audio_sync(url: str) -> Tuple[str, Dict[str, Any]]:
    """Đồng bộ: tải audio bằng yt-dlp, trả về (file_path, info).

    Ưu tiên m4a (native, không cần re-encode); fallback webm/best.
    Nếu video > MAX_AUDIO_SECONDS và ffmpeg khả dụng → chỉ tải phần đầu.
    """
    import yt_dlp  # import muộn để không chặn startup

    tmpdir = tempfile.mkdtemp(prefix="hoverai_audio_")

    # Bước 1: lấy info mà không tải
    info_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        cleanup_audio_tmpdir(tmpdir)
        raise RuntimeError(f"AUDIO_INFO_FAILED: {exc}") from exc

    duration = info.get("duration") or 0
    title = info.get("title", "")
    channel = info.get("uploader", "") or info.get("channel", "")
    platform = info.get("extractor_key", "YouTube")

    # Bước 2: tải audio
    output_template = os.path.join(tmpdir, "audio.%(ext)s")
    ydl_opts: Dict[str, Any] = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    # Nếu video dài → thử cắt (cần ffmpeg)
    if duration > MAX_AUDIO_SECONDS:
        try:
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
                None, [(0, MAX_AUDIO_SECONDS)]
            )
            logger.info(
                "FR3.5: video %ds > %ds, cắt về %ds đầu",
                duration, MAX_AUDIO_SECONDS, MAX_AUDIO_SECONDS,
            )
        except AttributeError:
            # yt-dlp cũ không có download_range_func → tải đủ, xử lý qua file size
            logger.warning("FR3.5: download_range_func không khả dụng, tải đủ audio.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        cleanup_audio_tmpdir(tmpdir)
        raise RuntimeError(f"AUDIO_DOWNLOAD_FAILED: {exc}") from exc

    # Bước 3: tìm file đã tải (bỏ qua .part)
    files = [f for f in os.listdir(tmpdir) if not f.endswith(".part")]
    if not files:
        cleanup_audio_tmpdir(tmpdir)
        raise RuntimeError("AUDIO_DOWNLOAD_FAILED: file không tìm thấy sau khi tải")

    audio_path = os.path.join(tmpdir, files[0])

    # Kiểm tra kích thước
    file_size = os.path.getsize(audio_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        cleanup_audio_tmpdir(tmpdir)
        raise RuntimeError(
            f"AUDIO_FILE_TOO_LARGE: {file_size // 1024 // 1024}MB > {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB"
        )

    logger.info(
        "FR3.5: tải xong audio — %s (%.1f MB, %ds)",
        os.path.basename(audio_path),
        file_size / 1024 / 1024,
        duration,
    )

    return audio_path, {
        "title": title,
        "duration": int(duration),
        "channel": channel,
        "platform": platform,
        "file_size": file_size,
    }


async def download_video_audio(url: str) -> Tuple[str, Dict[str, Any]]:
    """Async wrapper: tải audio video về máy.

    Returns:
        (audio_path, info_dict) — gọi cleanup_audio_tmpdir(os.path.dirname(audio_path)) sau khi dùng xong.

    Raises:
        RuntimeError với mã: AUDIO_INFO_FAILED | AUDIO_DOWNLOAD_FAILED | AUDIO_FILE_TOO_LARGE
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_audio_sync, url)

