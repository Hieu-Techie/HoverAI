from pydantic import BaseModel, HttpUrl
from typing import Optional, Any

class BaseResponse(BaseModel):
    """Response dùng cho kiểm tra trạng thái (health check) cơ bản của ứng dụng."""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None

class URLRequest(BaseModel):
    """Model dùng chung cho yêu cầu URL; hiện chưa có route dùng trực tiếp."""
    url: HttpUrl

class HealthResponse(BaseModel):
    """Module vận hành: schema response của endpoint /api/health."""
    status: str
    service: str
    version: str
    environment: str
