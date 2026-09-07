from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl
from app.services.url_safety import check_url_with_safe_browsing
from app.services.phishing_detector import check_phishing

router = APIRouter()

class URLCheckRequest(BaseModel):
    url: HttpUrl

class URLSafetyResponse(BaseModel):
    safe: bool
    threat_type: str

@router.post("/api/check-url-safety", response_model=URLSafetyResponse)
async def check_url_safety(request: URLCheckRequest):
    result = await check_url_with_safe_browsing(str(request.url))
    return URLSafetyResponse(
        safe=result["safe"],
        threat_type=result["threat_type"]
    )

# Models cho API Phishing (Task 4 & 5)
class PhishingRequest(BaseModel):
    href_url: HttpUrl
    anchor_text: str = Field(min_length=1, max_length=500)

class PhishingResponse(BaseModel):
    is_phishing: bool
    mismatch_warning: str

@router.post("/api/check-phishing", response_model=PhishingResponse)
async def detect_phishing(request: PhishingRequest):
    result = check_phishing(str(request.href_url), request.anchor_text)
    return PhishingResponse(
        is_phishing=result["is_phishing"],
        mismatch_warning=result["mismatch_warning"]
    )