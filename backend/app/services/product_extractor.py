"""Module 3, FR3.2: trích xuất thông tin sản phẩm từ JSON-LD, OpenGraph và Microdata."""

import asyncio
import json
from typing import Any, Dict, Optional

import aiohttp
from bs4 import BeautifulSoup

# Giới hạn HTML đầu vào (5 MB) để tránh OOM.
MAX_HTML_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 10
JINA_TIMEOUT_SECONDS = 15        # Jina cần thời gian render JS
JINA_MIN_TEXT_LENGTH = 100       # Bỏ qua nếu Jina trả về quá ít nội dung

# Header giả lập trình duyệt thật để tránh bị chặn.
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ---------------------------------------------------------------------------
# Kiểu dữ liệu chuẩn hóa đầu ra
# ---------------------------------------------------------------------------

def _empty_product() -> Dict[str, Optional[str]]:
    return {
        "name": None,
        "price": None,
        "currency": None,
        "rating": None,
        "review_count": None,
        "description": None,
        "brand": None,
        "image_url": None,
        "site_name": None,
        "sku": None,
    }


def _merge(base: Dict, update: Dict) -> Dict:
    """Ghi đè chỉ những trường chưa có trong base."""
    for key, value in update.items():
        if base.get(key) is None and value is not None:
            base[key] = value
    return base


# ---------------------------------------------------------------------------
# Lớp 1: JSON-LD Schema.org Product / Offer
# ---------------------------------------------------------------------------

def _extract_price_from_offer(offer: Any) -> tuple[Optional[str], Optional[str]]:
    """Trả về (price_str, currency) từ một Offer object hoặc list Offer."""
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    if not isinstance(offer, dict):
        return None, None
    price = offer.get("price") or offer.get("lowPrice")
    currency = offer.get("priceCurrency")
    return (str(price) if price is not None else None, currency)


def _extract_rating(aggregate: Any) -> tuple[Optional[str], Optional[str]]:
    """Trả về (rating_str, review_count) từ AggregateRating object."""
    if not isinstance(aggregate, dict):
        return None, None
    value = aggregate.get("ratingValue")
    best = aggregate.get("bestRating", 5)
    count = aggregate.get("reviewCount") or aggregate.get("ratingCount")
    rating_str = f"{value}/{best}" if value is not None else None
    return rating_str, (str(count) if count is not None else None)


def _parse_jsonld(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """FR3.2 lớp 1: đọc toàn bộ JSON-LD và trả về dict sản phẩm chuẩn hóa."""
    result = _empty_product()
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            raw = json.loads(script.string or script.get_text())
        except (TypeError, json.JSONDecodeError):
            continue
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if not any(str(t).lower() in {"product", "offer"} for t in types):
                continue
            # Tên sản phẩm
            result["name"] = result["name"] or item.get("name")
            # Mô tả
            result["description"] = result["description"] or item.get("description")
            # Thương hiệu
            brand = item.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            result["brand"] = result["brand"] or brand
            # Hình ảnh
            image = item.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")
            result["image_url"] = result["image_url"] or image
            # SKU/GTIN
            result["sku"] = result["sku"] or item.get("sku") or item.get("gtin")
            # Giá từ offers
            price, currency = _extract_price_from_offer(item.get("offers"))
            result["price"] = result["price"] or price
            result["currency"] = result["currency"] or currency
            # Đánh giá
            rating, count = _extract_rating(item.get("aggregateRating"))
            result["rating"] = result["rating"] or rating
            result["review_count"] = result["review_count"] or count
            # Nếu đã đủ thông tin cơ bản thì dừng sớm
            if result["name"] and result["price"]:
                return result
    return result


# ---------------------------------------------------------------------------
# Lớp 2: OpenGraph + meta tags
# ---------------------------------------------------------------------------

def _meta(soup: BeautifulSoup, prop: str = "", name: str = "") -> Optional[str]:
    """Trả về content của thẻ <meta> theo property hoặc name."""
    tag = None
    if prop:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"property": prop})
    if not tag and name:
        tag = soup.find("meta", attrs={"name": name})
    return (tag.get("content") or "").strip() or None if tag else None


def _parse_opengraph(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """FR3.2 lớp 2: đọc OpenGraph và meta tags thông dụng.

    Không dùng <title> tag ở đây — sẽ được xử lý với logic strip suffix ở lớp 4.
    """
    result = _empty_product()
    result["name"] = (
        _meta(soup, prop="og:title")
        or _meta(soup, name="twitter:title")
    )
    result["description"] = (
        _meta(soup, prop="og:description")
        or _meta(soup, name="description")
        or _meta(soup, name="twitter:description")
    )
    result["image_url"] = (
        _meta(soup, prop="og:image")
        or _meta(soup, name="twitter:image")
    )
    result["site_name"] = _meta(soup, prop="og:site_name")

    # Giá: OpenGraph Commerce / Facebook / Shopee format
    price = (
        _meta(soup, prop="product:price:amount")
        or _meta(soup, prop="og:price:amount")
        or _meta(soup, prop="product:sale_price:amount")
    )
    currency = (
        _meta(soup, prop="product:price:currency")
        or _meta(soup, prop="og:price:currency")
    )
    result["price"] = price
    result["currency"] = currency
    return result


# ---------------------------------------------------------------------------
# Lớp 3: Microdata (itemprop)
# ---------------------------------------------------------------------------

def _parse_microdata(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """FR3.2 lớp 3: đọc schema Microdata (itemprop attributes)."""
    result = _empty_product()

    def _itemprop(name: str) -> Optional[str]:
        tag = soup.find(attrs={"itemprop": name})
        if not tag:
            return None
        return (
            tag.get("content")
            or tag.get("value")
            or tag.get_text(strip=True)
            or None
        )

    result["name"] = _itemprop("name")
    result["description"] = _itemprop("description")
    result["price"] = _itemprop("price")
    result["currency"] = _itemprop("priceCurrency")
    result["rating"] = _itemprop("ratingValue")
    result["review_count"] = _itemprop("reviewCount")
    result["brand"] = _itemprop("brand") or _itemprop("manufacturer")
    result["image_url"] = _itemprop("image")
    result["sku"] = _itemprop("sku") or _itemprop("mpn")
    return result


# ---------------------------------------------------------------------------
# Hàm tiện ích: format giá và đánh giá
# ---------------------------------------------------------------------------

def _format_price(price: Optional[str], currency: Optional[str]) -> Optional[str]:
    if not price:
        return None
    currency_symbols = {
        "VND": "₫", "USD": "$", "EUR": "€", "GBP": "£",
        "JPY": "¥", "KRW": "₩", "CNY": "¥", "SGD": "S$",
    }
    symbol = currency_symbols.get((currency or "").upper(), currency or "")
    # Nếu currency là ký hiệu đơn ký tự thì đặt trước, ngược lại đặt sau.
    if symbol and len(symbol) <= 1:
        return f"{symbol}{price}"
    return f"{price} {symbol}".strip()


def _format_rating(rating: Optional[str], review_count: Optional[str]) -> Optional[str]:
    if not rating:
        return None
    if review_count:
        return f"{rating} ({review_count} đánh giá)"
    return rating


# ---------------------------------------------------------------------------
# Entry-point công khai
# ---------------------------------------------------------------------------

def _extract_name_fallback(soup: BeautifulSoup, site_name: Optional[str]) -> Optional[str]:
    """Lớp 4: lấy tên sản phẩm từ thẻ h1 hoặc title nếu các lớp trước thất bại.

    Lọc bỏ các tiêu đề chung chung của website (VD: "Shopee | Mua sắm online").
    """
    import re as _re

    # Thử h1 trước — thường là tên sản phẩm trên trang chi tiết
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
        if name and len(name) > 3:
            return name

    # Thử thẻ <title> — lọc bỏ hậu tố thương hiệu site (VD: " | Shopee", " - Tiki")
    if soup.title and soup.title.string:
        raw_title = soup.title.string.strip()
        # Bỏ hậu tố "| SiteName" hoặc "- SiteName" ở cuối
        cleaned = _re.sub(r'\s*[\|–\-]\s*.{2,30}$', '', raw_title).strip()
        if not cleaned:
            cleaned = raw_title

        # Nếu kết quả chỉ là tên site (ngắn ≤ 10 ký tự hoặc trùng site_name) → bỏ qua
        if site_name and cleaned.lower() == site_name.lower():
            return None
        if len(cleaned) > 10:
            return cleaned

    return None


def extract_product_from_html(url: str, html: str) -> Dict[str, Any]:
    """FR3.2: trích xuất thông tin sản phẩm từ HTML đã render.

    Thứ tự ưu tiên: JSON-LD → OpenGraph → Microdata → H1/Title fallback.
    Trả về dict chuẩn hóa với các trường đã format sẵn.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Chạy cả 3 lớp rồi merge theo thứ tự ưu tiên.
    jsonld = _parse_jsonld(soup)
    og = _parse_opengraph(soup)
    micro = _parse_microdata(soup)

    product = _empty_product()
    _merge(product, jsonld)
    _merge(product, og)
    _merge(product, micro)

    # Lớp 4: fallback h1/title nếu chưa có tên.
    if not product.get("name"):
        fallback_name = _extract_name_fallback(soup, product.get("site_name"))
        if fallback_name:
            product["name"] = fallback_name

    # Format lại các trường hiển thị.
    product["price_display"] = _format_price(product["price"], product["currency"])
    product["rating_display"] = _format_rating(product["rating"], product["review_count"])

    # Thông tin nguồn
    product["url"] = url

    return product


async def _jina_enrich_product(url: str, product: Dict[str, Any]) -> None:
    """FR3.2 lớp 5: dùng Jina Reader để render JS và lấy tên/mô tả sản phẩm cho SPA.

    Jina trả về Markdown đã render — parse heading đầu tiên làm tên sản phẩm,
    đoạn văn đầu tiên có nghĩa làm mô tả. Cập nhật product dict in-place.
    Không raise — nếu thất bại thì im lặng, giữ nguyên product cũ.
    """
    jina_url = f"https://r.jina.ai/{url}"
    _headers = {
        "Accept": "text/markdown, text/plain;q=0.9",
        "User-Agent": _FETCH_HEADERS["User-Agent"],
    }
    try:
        timeout = aiohttp.ClientTimeout(total=JINA_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout, headers=_headers) as session:
            async with session.get(jina_url) as resp:
                if resp.status >= 400:
                    return
                text = (await resp.read()).decode("utf-8", errors="replace").strip()
    except Exception:
        return

    if len(text) < JINA_MIN_TEXT_LENGTH:
        return

    lines = text.splitlines()

    # --- Tên sản phẩm: heading đầu tiên (# ...) hoặc dòng Title: ...
    # Jina thường bắt đầu bằng: Title: <product name> | <site name>
    import re as _re
    _SITE_SUFFIX_RE = _re.compile(r'\s*[\|–\-]\s*[^|–\-]{2,40}$')

    name_found: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("title:"):
            candidate = stripped.split(":", 1)[1].strip()
            # Bỏ hậu tố "| Shopee Việt Nam", "- Lazada VN", ...
            candidate = _SITE_SUFFIX_RE.sub("", candidate).strip()
            if len(candidate) > 10:
                name_found = candidate[:200]
                break
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            candidate = _SITE_SUFFIX_RE.sub("", candidate).strip()
            if len(candidate) > 10:
                name_found = candidate[:200]
                break

    # --- Mô tả: đoạn văn đầu tiên có ít nhất 30 ký tự, không phải heading/link
    desc_found: Optional[str] = None
    for line in lines:
        stripped = line.strip()
        if (
            len(stripped) >= 30
            and not stripped.startswith("#")
            and not stripped.startswith("!")
            and not stripped.startswith("[")
            and not stripped.startswith("|")
            and "http" not in stripped[:20]
        ):
            desc_found = stripped[:500]
            break

    # Chỉ cập nhật nếu hiện tại chưa có dữ liệu
    if name_found and not product.get("name"):
        product["name"] = name_found
        product["extraction_note"] = "JINA_PARTIAL"
    if desc_found and not product.get("description"):
        product["description"] = desc_found


async def fetch_and_extract_product(url: str) -> Dict[str, Any]:
    """FR3.2: tải HTML từ URL rồi trích xuất sản phẩm (dùng khi extension không gửi HTML).

    Pipeline 5 lớp:
    1-3. JSON-LD / OpenGraph / Microdata từ HTML tĩnh
    4.   H1 / <title> tag fallback
    5.   Jina Reader (render JS) — chỉ khi các lớp trên thất bại (SPA_PARTIAL)

    Chỉ raise RuntimeError khi không thể kết nối mạng hoàn toàn.
    """
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(headers=_FETCH_HEADERS, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True, max_redirects=5) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"PRODUCT_FETCH_FAILED: HTTP {resp.status}")
                raw = await resp.read()
                html = raw[:MAX_HTML_BYTES].decode("utf-8", errors="replace")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"PRODUCT_FETCH_FAILED: {exc}") from exc

    product = extract_product_from_html(url, html)

    has_name = bool(product.get("name"))
    has_price = bool(product.get("price"))

    if not has_name:
        # Lớp 5: Jina Reader — render JavaScript để lấy tên từ SPA.
        product["extraction_note"] = "SPA_PARTIAL"
        await _jina_enrich_product(url, product)
        has_name = bool(product.get("name"))

    if not has_name:
        product["extraction_note"] = "SPA_PARTIAL"
    elif not has_price:
        # Giữ JINA_PARTIAL nếu đã được set bởi Jina
        if product.get("extraction_note") != "JINA_PARTIAL":
            product["extraction_note"] = "PRICE_NOT_AVAILABLE"
    else:
        product["extraction_note"] = "OK"

    return product

