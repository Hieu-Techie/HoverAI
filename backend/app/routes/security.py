from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl
from app.services.url_safety import check_url_with_safe_browsing
from app.services.phishing_detector import check_phishing

# Module 2: API kiểm tra an toàn URL và phát hiện link ngụy trang.
router = APIRouter()

class URLCheckRequest(BaseModel):
    """FR2.1: URL cần gửi tới Google Safe Browsing."""
    url: HttpUrl

class URLSafetyResponse(BaseModel):
    """FR2.1: trạng thái an toàn và loại mối đe dọa trả về cho client."""
    safe: bool
    threat_type: str

@router.post("/api/check-url-safety", response_model=URLSafetyResponse)
async def check_url_safety(request: URLCheckRequest):
    """FR2.1: nhận URL, gọi service Safe Browsing và trả kết quả chuẩn hóa."""
    result = await check_url_with_safe_browsing(str(request.url))
    return URLSafetyResponse(
        safe=result["safe"],
        threat_type=result["threat_type"]
    )

class PhishingRequest(BaseModel):
    """FR2.2: URL đích và text hiển thị của anchor cần đối chiếu."""
    href_url: HttpUrl
    anchor_text: str = Field(min_length=1, max_length=500)

class PhishingResponse(BaseModel):
    """FR2.2: kết quả phát hiện domain hiển thị khác domain đích."""
    is_phishing: bool
    mismatch_warning: str

@router.post("/api/check-phishing", response_model=PhishingResponse)
async def detect_phishing(request: PhishingRequest):
    """FR2.2: gọi detector domain và trả cảnh báo phishing cho extension."""
    result = check_phishing(str(request.href_url), request.anchor_text)
    return PhishingResponse(
        is_phishing=result["is_phishing"],
        mismatch_warning=result["mismatch_warning"]
    )