from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class ProductExtractionRequest(BaseModel):
    url: HttpUrl
    html: Optional[str] = Field(default=None, max_length=5 * 1024 * 1024)
    gemini_api_key: Optional[str] = Field(default=None, max_length=200)

class ProductExtractionResponse(BaseModel):
    """FR3.2: kết quả trích xuất sản phẩm với các trường chuyên biệt."""
    url: HttpUrl
    content_type: str = "product"
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[str] = None
    price_display: Optional[str] = None
    currency: Optional[str] = None
    rating: Optional[str] = None
    rating_display: Optional[str] = None
    review_count: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    site_name: Optional[str] = None
    sku: Optional[str] = None
    summary: Optional[str] = None
