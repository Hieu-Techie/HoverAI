from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class ContentExtractionRequest(BaseModel):
    url: HttpUrl
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)

class ContentExtractionResponse(BaseModel):
    url: HttpUrl
    method: str
    title: str
    text: str
    metadata: dict
    content_type: str
    summary: Optional[str] = None

class HtmlContentExtractionRequest(BaseModel):
    url: HttpUrl
    html: str = Field(min_length=1, max_length=5 * 1024 * 1024)
    page_title: str = Field(default="", max_length=500)
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)
