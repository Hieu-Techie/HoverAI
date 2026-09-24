from fastapi import APIRouter
from app.models.security import URLCheckRequest, URLSafetyResponse, PhishingRequest, PhishingResponse
from app.services.security.url_safety import check_url_with_safe_browsing
from app.services.security.phishing_detector import check_phishing

# Module 2: API kiểm tra an toàn URL và phát hiện link ngụy trang.
router = APIRouter()


@router.post("/api/check-url-safety", response_model=URLSafetyResponse)
async def check_url_safety(request: URLCheckRequest):
    """FR2.1: nhận URL, gọi service Safe Browsing và trả kết quả chuẩn hóa."""
    result = await check_url_with_safe_browsing(str(request.url))
    return URLSafetyResponse(
        safe=result["safe"],
        threat_type=result["threat_type"]
    )


@router.post("/api/check-phishing", response_model=PhishingResponse)
async def detect_phishing(request: PhishingRequest):
    """FR2.2: gọi detector domain và trả cảnh báo phishing cho extension."""
    result = check_phishing(str(request.href_url), request.anchor_text)
    return PhishingResponse(
        is_phishing=result["is_phishing"],
        mismatch_warning=result["mismatch_warning"]
    )