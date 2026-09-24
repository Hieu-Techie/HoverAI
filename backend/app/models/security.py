from pydantic import BaseModel, Field, HttpUrl

class URLCheckRequest(BaseModel):
    url: HttpUrl

class URLSafetyResponse(BaseModel):
    safe: bool
    threat_type: str

class PhishingRequest(BaseModel):
    href_url: HttpUrl
    anchor_text: str = Field(min_length=1, max_length=500)

class PhishingResponse(BaseModel):
    is_phishing: bool
    mismatch_warning: str
