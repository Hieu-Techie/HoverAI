import os
import aiohttp
import asyncio
from cachetools import TTLCache
from dotenv import load_dotenv

# Module 2, FR2.1: lớp bao bất đồng bộ cho Google Safe Browsing và cache kết quả.
load_dotenv()
SAFE_BROWSING_API_KEY = os.getenv("SAFE_BROWSING_API_KEY")

# Cache lưu tối đa 1.000 URL trong 1 giờ để giảm số lần gọi API.
url_cache = TTLCache(maxsize=1000, ttl=3600)

async def check_url_with_safe_browsing(url: str) -> dict:
    """FR2.1: kiểm tra URL, cache 1 giờ và fail-closed khi không xác minh được."""
    # Trả về ngay lập tức nếu URL đã được quét trước đó
    if url in url_cache:
        return url_cache[url]

    if not SAFE_BROWSING_API_KEY:
        return {"safe": False, "threat_type": "API_KEY_MISSING"}

    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={SAFE_BROWSING_API_KEY}"
    payload = {
        "client": {"clientId": "hoverai", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    # Ép buộc timeout tối đa 1.4 giây để đảm bảo FR2.1 (< 1.5s)
    timeout = aiohttp.ClientTimeout(total=1.4)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get("matches", [])
                    
                    if matches:
                        result = {"safe": False, "threat_type": matches[0]["threatType"]}
                    else:
                        result = {"safe": True, "threat_type": "NONE"}
                        
                    url_cache[url] = result
                    return result
                return {"safe": False, "threat_type": f"API_ERROR_{response.status}"}
    except asyncio.TimeoutError:
        return {"safe": False, "threat_type": "TIMEOUT"}
    except Exception:
        return {"safe": False, "threat_type": "UNKNOWN_ERROR"}