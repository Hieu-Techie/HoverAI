from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class VideoMetadataRequest(BaseModel):
    url: HttpUrl
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5000)
    channel: str = Field(default="", max_length=200)
    platform: str = Field(default="video", max_length=50)  # FR3.4: nền tảng video (youtube, tiktok...)
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)

class VideoMetadataResponse(BaseModel):
    """FR3.4: kết quả tóm tắt dự đoán với cảnh báo clickbait."""
    title_vi: Optional[str] = None
    summary: Optional[str] = None
    is_prediction: bool = True
    warning: str = ""

class DeepScanRequest(BaseModel):
    url: HttpUrl
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)
    yt_cookie_header: Optional[str] = Field(default=None, max_length=20000)  # Cookie string từ extension

class DeepScanResponse(BaseModel):
    url: str
    title: str
    title_vi: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[str] = None
    duration: Optional[int] = None
    channel: Optional[str] = None
    platform: Optional[str] = None
    is_deep_scan: bool = True
