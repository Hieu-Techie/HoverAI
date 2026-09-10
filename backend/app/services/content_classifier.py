"""Module 3: phân loại URL/HTML trước khi chọn bộ xử lý nội dung."""

import json
import re
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


class ContentType(str, Enum):
    ARTICLE = "article"
    PRODUCT = "product"
    VIDEO = "video"
    UNKNOWN = "unknown"


VIDEO_HOSTS = {
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
}
VIDEO_EXTENSIONS = (".mp4", ".webm", ".m3u8", ".mov", ".avi")

PRODUCT_PATH_MARKERS = ("/product/", "/products/", "/item/", "/dp/", "/p/", "/pd/")

# Tên miền thương mại điện tử nổi tiếng — URL từ các site này sẽ được ưu tiên
# nhận diện là sản phẩm (trừ khi path rõ ràng là không phải product).
ECOMMERCE_DOMAINS = {
    # Việt Nam
    "shopee.vn",
    "tiki.vn",
    "lazada.vn",
    "sendo.vn",
    "thegioididong.com",
    "cellphones.com.vn",
    "fptshop.com.vn",
    "dienmayxanh.com",
    "bachhoaxanh.com",
    "hasaki.vn",
    "adayroi.com",
    # Quốc tế
    "shopee.com",
    "shopee.sg",
    "shopee.ph",
    "shopee.my",
    "shopee.th",
    "shopee.co.id",
    "amazon.com",
    "amazon.co.uk",
    "amazon.de",
    "amazon.fr",
    "amazon.co.jp",
    "amazon.com.au",
    "ebay.com",
    "ebay.co.uk",
    "aliexpress.com",
    "taobao.com",
    "jd.com",
    "lazada.com",
    "lazada.sg",
    "flipkart.com",
    "walmart.com",
    "target.com",
}

# Prefix path rõ ràng là KHÔNG phải trang sản phẩm (trang chủ, tìm kiếm, ...).
_NON_PRODUCT_PATH_PREFIXES = (
    "/search",
    "/category",
    "/categories",
    "/collection",
    "/collections",
    "/brand",
    "/brands",
    "/shop/",
    "/seller/",
    "/chat",
    "/user",
    "/profile",
    "/help",
    "/about",
    "/cart",
    "/gio-hang",
    "/checkout",
    "/login",
    "/signup",
    "/register",
    "/voucher",
    "/flash-sale",
    "/mall",
    "/blog",
)

# Pattern URL sản phẩm Shopee: /ten-san-pham-i.seller_id.item_id
_SHOPEE_ITEM_RE = re.compile(r"-i\.\d+\.\d+", re.IGNORECASE)

# Pattern chung: path chứa đoạn toàn số dài ≥ 6 chữ số (thường là product/item ID)
_NUMERIC_ID_RE = re.compile(r"(?<![a-z])\d{6,}(?![a-z])")


def _is_subdomain_of(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def _is_ecommerce_product_path(path: str) -> bool:
    """Heuristic: trả True nếu path trên e-commerce site trông như trang sản phẩm."""
    if not path or path in ("/", ""):
        return False  # homepage
    path_lower = path.lower()
    # Loại trừ các path rõ ràng không phải sản phẩm
    if any(path_lower.startswith(p) for p in _NON_PRODUCT_PATH_PREFIXES):
        return False
    # Shopee item URL: /ten-san-pham-i.123456.789012
    if _SHOPEE_ITEM_RE.search(path):
        return True
    # Path chứa product/item ID dạng số dài
    if _NUMERIC_ID_RE.search(path):
        return True
    # Có ít nhất 1 path segment (không phải root)
    parts = [p for p in path.split("/") if p]
    return len(parts) >= 1


def _has_product_structured_data(html: str) -> bool:
    """FR3.2 nền tảng: nhận diện schema Product/Offer không theo từng website."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (TypeError, json.JSONDecodeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            types = candidate.get("@type", [])
            types = types if isinstance(types, list) else [types]
            if any(str(value).lower() in {"product", "offer"} for value in types):
                return True
    return bool(soup.select_one('meta[property="og:type"][content="product"]'))


def detect_content_type(url: str, html: Optional[str] = None) -> ContentType:
    """FR3 dispatcher: ưu tiên nhận diện video/sản phẩm, còn lại xem là bài viết.

    Thứ tự kiểm tra:
    1. Video host / video extension
    2. PRODUCT_PATH_MARKERS chung (/product/, /dp/, ...)
    3. Domain thương mại điện tử nổi tiếng + heuristic path
    4. HTML structured data (JSON-LD Product hoặc og:type=product)
    5. Mặc định → article
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path

    # --- Video ---
    if any(_is_subdomain_of(hostname, host) for host in VIDEO_HOSTS):
        return ContentType.VIDEO
    if path.lower().endswith(VIDEO_EXTENSIONS):
        return ContentType.VIDEO

    # --- Product (path markers chung) ---
    if any(marker in path.lower() for marker in PRODUCT_PATH_MARKERS):
        return ContentType.PRODUCT

    # --- Product (e-commerce domain + path heuristic) ---
    if any(_is_subdomain_of(hostname, domain) for domain in ECOMMERCE_DOMAINS):
        if _is_ecommerce_product_path(path):
            return ContentType.PRODUCT

    # --- Product (structured data trong HTML đã render) ---
    if html and _has_product_structured_data(html):
        return ContentType.PRODUCT

    return ContentType.ARTICLE
