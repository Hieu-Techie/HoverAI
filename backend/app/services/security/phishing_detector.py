from urllib.parse import urlparse

# Module 2, FR2.2: chuẩn hóa hostname và phát hiện domain hiển thị giả mạo.
# FR2.2: alias cho các dịch vụ có domain rút gọn hoặc domain di động.
KNOWN_ALIASES = {
    "youtu.be": "youtube.com",
    "m.youtube.com": "youtube.com",
    "fb.com": "facebook.com",
    "m.facebook.com": "facebook.com",
    "t.co": "twitter.com",
    "x.com": "twitter.com",
    "instagr.am": "instagram.com",
    "amazon.co.uk": "amazon.com",
    "amzn.to": "amazon.com"
}

MULTI_PART_SUFFIXES = {"co.uk", "com.au", "co.jp", "com.br", "co.in"}

def get_base_domain(url_or_text: str) -> str:
    """FR2.2: bóc tách hostname từ URL đích hoặc anchor text."""
    if not url_or_text:
        return ""
        
    url_or_text = url_or_text.strip()
    if not url_or_text:
        return ""

    # Thêm scheme để urllib parse chính xác nếu text chỉ là dạng 'youtube.com'
    if "://" not in url_or_text:
        url_or_text = "http://" + url_or_text
        
    try:
        parsed = urlparse(url_or_text)
        domain = parsed.hostname or ""
        domain = domain.rstrip(".").lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def normalize_domain(domain: str) -> str:
    """FR2.2: chuẩn hóa alias và lấy registrable domain để so sánh."""
    if not domain:
        return ""
        
    domain = domain.rstrip(".").lower()
    if domain in KNOWN_ALIASES:
        return KNOWN_ALIASES[domain]

    # Giữ lại registrable domain, kể cả các public suffix phổ biến như co.uk.
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain

    suffix_length = 2 if ".".join(parts[-2:]) in MULTI_PART_SUFFIXES else 1
    base_domain = ".".join(parts[-(suffix_length + 1):])
    return KNOWN_ALIASES.get(base_domain, base_domain)

def check_phishing(href_url: str, anchor_text: str) -> dict:
    """FR2.2: cảnh báo khi anchor domain không trùng domain đích hợp lệ."""
    # Nếu text hiển thị không mang dáng dấp của một URL (không có dấu chấm hoặc chứa dấu cách)
    # thì không cần kiểm tra phishing ngụy trang tên miền.
    if not anchor_text or "." not in anchor_text or any(char.isspace() for char in anchor_text):
        return {"is_phishing": False, "mismatch_warning": "NONE"}

    href_domain = get_base_domain(href_url)
    text_domain = get_base_domain(anchor_text)

    if not href_domain or not text_domain:
        return {"is_phishing": False, "mismatch_warning": "NONE"}

    norm_href = normalize_domain(href_domain)
    norm_text = normalize_domain(text_domain)

    # Chỉ chấp nhận cùng domain hoặc subdomain thật sự, không chấp nhận
    # các chuỗi giả mạo như evil-youtube.com.
    same_domain = (
        norm_href == norm_text
        or href_domain == norm_text
        or href_domain.endswith(f".{norm_text}")
    )
    if not same_domain:
        return {
            "is_phishing": True, 
            "mismatch_warning": f"Cảnh báo: Liên kết hiển thị là [{text_domain}] nhưng lại chuyển hướng ngầm đến [{href_domain}]"
        }

    return {"is_phishing": False, "mismatch_warning": "NONE"}