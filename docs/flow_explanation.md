# HoverAI — Giải thích chi tiết luồng hoạt động

> **Dành cho:** Dev mới tham gia dự án, review code, debugging  
> **Cập nhật:** 2026-09-24

---

## Mục lục

1. [Khởi động hệ thống](#1-khởi-động-hệ-thống)
2. [Luồng chính: Alt + Hover](#2-luồng-chính-alt--hover)
3. [Bảo mật (FR2)](#3-bảo-mật-fr2)
4. [Trích xuất bài viết (FR3.1)](#4-trích-xuất-bài-viết-fr31)
5. [Trích xuất sản phẩm (FR3.2)](#5-trích-xuất-sản-phẩm-fr32)
6. [Trích xuất video (FR3.3–3.4)](#6-trích-xuất-video-fr33--fr34)
7. [Deep Scan audio (FR3.5)](#7-deep-scan-audio-fr35)
8. [Phân tích trang hiện tại (click icon)](#8-phân-tích-trang-hiện-tại-click-icon)
9. [Kết nối Frontend ↔ Backend](#9-kết-nối-frontend--backend)
10. [Chi tiết từng file](#10-chi-tiết-từng-file)

---

## 1. Khởi động hệ thống

### Backend khởi động

```
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**`backend/app/main.py` thực hiện theo thứ tự:**

1. `from dotenv import load_dotenv; load_dotenv()` — Đọc file `.env` vào environment. **PHẢI đứng trước mọi project import** vì các module như `url_safety.py` đọc `os.getenv("SAFE_BROWSING_API_KEY")` tại thời điểm import (module-level).

2. Import các route module (`security`, `content`, `deepscan`) — Python tự động import toàn bộ chuỗi dependency: route → service → extractor/summarizer.

3. Tạo `FastAPI()` app, cấu hình CORS (`allow_origins=["*"]` trong dev), thêm logging middleware.

4. Register routers: `app.include_router(security.router)`, `content.router`, `deepscan.router`.

5. Định nghĩa `GET /api/health` trực tiếp trong main.py.

### Extension load

Chrome inject 5 file JS vào mọi trang web theo thứ tự khai báo trong `manifest.json`:

```
src/config.js → src/utils.js → src/api.js → src/ui.js → src/content.js
```

**Thứ tự quan trọng vì:**
- `config.js` khai báo biến global (`let popup`, `let currentVideoUrl`, v.v.) — các file sau dùng những biến này
- `ui.js` inject HTML popup vào DOM và bind DOM refs — `content.js` cần DOM đã sẵn sàng để thêm event listener

---

## 2. Luồng chính: Alt + Hover

### Bước 1: Phát hiện hover (`content.js`)

```javascript
document.addEventListener('keydown', e => { if (e.key === 'Alt') isAltPressed = true; });
document.addEventListener('mouseover', e => {
    let target = e.target.closest('a');
    if (target && target.href && isAltPressed) {
        // debounce 300ms để tránh spam API khi user di chuột nhanh
        clearTimeout(hoverDebounceTimer);
        hoverDebounceTimer = setTimeout(() => { ... }, 300);
    }
});
```

`HOVER_DEBOUNCE_DELAY = 300ms` — chỉ trigger sau 300ms dừng lại trên link.

### Bước 2: Chuẩn bị dữ liệu

`utils.js` → `extractAndNormalizeURL(target)`:
- Lấy `href` từ element `<a>`
- Normalize URL (loại bỏ tracking params)
- Trích xuất `domain` từ URL
- Kiểm tra validity: bỏ qua `javascript:`, `#anchor`, `mailto:`, URL thiếu host

`utils.js` → `extractAnchorText(target)`:
- Lấy text hiển thị của link (dùng để phát hiện phishing)

### Bước 3: Show popup + loading state

`ui.js` → `setLoadingState()`:
- Reset tất cả nội dung popup
- Set trạng thái ⏳ loading
- Ẩn Deep Scan button

`utils.js` → `calculateSmartPosition(clientX, clientY)`:
- Tính vị trí popup cạnh con trỏ
- Đảm bảo popup không vượt ra ngoài viewport

### Bước 4: Gọi API song song

`content.js` sử dụng `analysisSequence` counter để tránh race condition (user hover link A, rồi link B trước khi A xong → bỏ kết quả A):

```javascript
const analysisId = ++analysisSequence;
checkSecurity(currentLinkData).then(result => {
    if (analysisId === analysisSequence) {  // vẫn là link hiện tại?
        showSecurityResult(result);
        extractTargetLinkContent(currentLinkData).then(content => { ... });
    }
});
```

Security check và content extraction chạy **tuần tự** (security trước, content sau) — không song song. Security phải xong trước để hiển thị kết quả bảo mật nhanh.

Tuy nhiên trong `checkSecurity()` ở `api.js`, **Safe Browsing và phishing check chạy song song**:
```javascript
const [safety, phishing] = await Promise.all([
    fetchJson('/api/check-url-safety', { url }),
    fetchJson('/api/check-phishing', { href_url, anchor_text })
]);
```

---

## 3. Bảo mật (FR2)

### 3.1 Safe Browsing (`url_safety.py`)

**API:** Google Safe Browsing Lookup API v4  
**Endpoint:** `POST https://safebrowsing.googleapis.com/v4/threatMatches:find`

Gửi URL lên Google để kiểm tra có trong danh sách đe dọa (MALWARE, PHISHING, SOCIAL_ENGINEERING, UNWANTED_SOFTWARE).

**Xử lý kết quả:**
- Tìm thấy match → `{safe: False, threat_type: "MALWARE"}`
- Không match → `{safe: True, threat_type: "SAFE"}`
- Key trống → `{safe: True, threat_type: "API_KEY_MISSING"}` (soft fail, không chặn user)
- Timeout/error → `{safe: True, threat_type: "TIMEOUT"}` (soft fail)

**UI hiển thị** (`ui.js` → `showSecurityResult()`):
- ✅ Liên kết an toàn
- ⚠️ Không thể xác minh (API_KEY_MISSING)
- ⚠️ CẢNH BÁO: URL nguy hiểm

### 3.2 Phishing Detection (`phishing_detector.py`)

Logic đơn giản: so sánh domain **hiển thị trong text link** với domain **thực sự trong URL href**.

Ví dụ: `<a href="https://shopee.vn">Xem thêm tại vnexpress.net</a>`  
→ Text domain: `vnexpress.net` ≠ Actual domain: `shopee.vn` → `is_phishing: True`

---

## 4. Trích xuất bài viết (FR3.1)

### Pipeline 4 bước (content_extractor.py)

**Khi trỏ chuột vào link** → Backend tự fetch HTML (không cần user mở trang):

#### Bước 1: Fetch HTML (`_fetch_html`)
```python
aiohttp.ClientSession.get(url, headers={User-Agent: Chrome/131})
```
- Timeout: 10s, max 5MB
- Retry 3 lần nếu HTML rỗng hoặc bot challenge
- Raise `SOURCE_BOT_CHALLENGE` nếu phát hiện Cloudflare "Just a moment..."

#### Bước 2: Trafilatura (`_extract_with_trafilatura`)
```python
trafilatura.extract(html, favor_precision=True, include_comments=False)
```
- **Tốt nhất** cho bài báo: loại bỏ nav, footer, quảng cáo, giữ nội dung chính
- Nếu < 80 ký tự hoặc bị đánh giá là low-quality → sang bước 3

**Low quality check** (`_is_low_quality_content`):
- text < 300 ký tự VÀ có ≥2 nav/header/footer elements
- hoặc nav text > 50% text length

#### Bước 3: Newspaper3k (`_extract_with_newspaper`)
```python
article = Article(url); article.set_html(html); article.parse()
```
- Fallback khi Trafilatura thất bại
- Thử BeautifulSoup `<article>, <main>` nếu Newspaper không lấy được text

#### Bước 4: Jina Reader (`_extract_with_jina`)
```python
httpx.get(f"https://r.jina.ai/{url}")  # sync, trong executor
```
- Fallback cuối cùng khi HTML server-side không có nội dung (SPA, JS-only)
- **Đặc biệt:** KHÔNG dùng custom User-Agent vì Jina/Cloudflare block Chrome UA giả mạo
- Chạy trong `asyncio.get_running_loop().run_in_executor()` (sync trong async context)

**Khi user mở trang và click icon** → Extension gửi HTML đã render bằng trình duyệt:  
`POST /api/extract-content-from-html {url, html, page_title}`  
→ Bỏ qua bước 1 fetch, vào thẳng bước 2.

### Tóm tắt bài viết (`article_summarizer.py`)
```python
genai.Client(api_key=key).aio.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    contents=f"Tóm tắt bài viết sau bằng tiếng Việt: {text}"
)
```

---

## 5. Trích xuất sản phẩm (FR3.2)

### 5 lớp trích xuất (`product_extractor.py`)

Shopee/Lazada được xử lý đặc biệt qua `fetch-shopee-product` message đến `background.js` (gọi Shopee internal API với cookie của user đang đăng nhập).

Với các trang thương mại điện tử thông thường, pipeline 5 lớp:

#### Layer 1: JSON-LD
```html
<script type="application/ld+json">
  {"@type": "Product", "name": "...", "offers": {"price": "..."}}
</script>
```
Chuẩn schema.org, đáng tin cậy nhất, phổ biến trên Tiki, Sendo, WooCommerce.

#### Layer 2: Open Graph
```html
<meta property="og:title" content="...">
<meta property="product:price:amount" content="...">
```
Facebook meta tags — rất phổ biến, thường có giá và mô tả.

#### Layer 3: Microdata
```html
<div itemtype="https://schema.org/Product">
  <span itemprop="name">...</span>
```
Cũ hơn JSON-LD nhưng vẫn dùng.

#### Layer 4: H1 + meta
BeautifulSoup tìm `<h1>` làm tên sản phẩm, `<meta name="description">` làm mô tả.

#### Layer 5: Jina Reader
Gọi `r.jina.ai` để render JavaScript, parse markdown output tìm tên và mô tả.

**Extraction notes:**
- `SPA_PARTIAL` → Trang dùng JS, không có đủ data trong HTML tĩnh
- `JINA_PARTIAL` → Jina lấy được tên nhưng không có giá
- `PRICE_NOT_AVAILABLE` → Không tìm thấy giá ở bất kỳ layer nào

### Tóm tắt sản phẩm (`product_summarizer.py`)
Gemini chuẩn hóa tên (tiếng Việt), highlight điểm nổi bật (spec, ưu điểm nổi bật của giá).

---

## 6. Trích xuất video (FR3.3 + FR3.4)

### Phân loại nền tảng (`content_classifier.py`)
```python
if "youtube.com/watch" in url or "youtu.be/" in url:
    return ContentType.VIDEO
if "tiktok.com" in url or "vm.tiktok.com" in url:
    return ContentType.VIDEO
if "vimeo.com" in url:
    return ContentType.VIDEO
```

### YouTube flow (`video_extractor.py`)

**Bước 1:** `YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en', 'en-US'])`
- Ưu tiên: tiếng Việt → tiếng Anh → tự động
- Nếu thành công: `extraction_note = None`, `is_prediction = False`

**Bước 2 (fallback):** `yt-dlp` lấy metadata
```python
yt_dlp.YoutubeDL({'skip_download': True}).extract_info(url)
```
- `extraction_note = "TRANSCRIPT_DISABLED"` / `"TRANSCRIPT_NOT_FOUND"` / `"TRANSCRIPT_ERROR"`
- `is_prediction = True`

### Non-YouTube flow (TikTok, Vimeo, v.v.)
Luôn dùng `yt-dlp` lấy metadata (title, description, channel, duration).
- `extraction_note = "TRANSCRIPT_NOT_AVAILABLE"` (nền tảng không hỗ trợ)
- `is_prediction = True`

### Tóm tắt video (`video_summarizer.py`)

**Với transcript (is_prediction=False):**
```
Gemini: "Tóm tắt nội dung video YouTube dựa trên transcript sau: {transcript_text}"
```

**Với metadata only (is_prediction=True):**
```
Gemini: "Dựa trên tiêu đề và mô tả sau, hãy dự đoán nội dung video (ghi rõ đây là dự đoán): {title}\n{description}"
```

### UI thể hiện (`ui.js` → `showVideoResult()`)

| is_prediction | extraction_note | Hiển thị |
|---|---|---|
| `False` | `null` | "Phụ đề: Tiếng Việt (tự động)" + tóm tắt chuẩn |
| `True` | `TRANSCRIPT_NOT_AVAILABLE` + có description | "📋 Phân tích AI (từ mô tả video)" |
| `True` | bất kỳ | "⚠️ Phân tích AI (dự đoán từ tiêu đề)" |

**Deep Scan button** chỉ hiện khi `is_prediction = True` hoặc transcript không lấy được.

---

## 7. Deep Scan Audio (FR3.5)

### Kích hoạt
User click "🔍 Deep Scan (Quét âm thanh nâng cao)" — chỉ xuất hiện khi không có transcript.

### Luồng kỹ thuật

**`content.js`** → `chrome.runtime.connect({name: 'hoverai-deepscan'})`  
→ port.postMessage({type: 'start-deepscan', url: currentVideoUrl})

**`background.js`** (service worker, không bị CSP) nhận kết nối:
```javascript
chrome.runtime.onConnect.addListener(port => {
    if (port.name !== 'hoverai-deepscan') return;
    port.onMessage.addListener(async msg => {
        const resp = await fetch('http://127.0.0.1:8000/api/deepscan-audio', {...});
        port.postMessage({ok: true, data: await resp.json()});
    });
});
```

> **Tại sao không dùng fetch() trực tiếp từ content.js?**  
> TikTok, YouTube có Content Security Policy (CSP) header chặn kết nối từ trang của họ đến `localhost`. Background service worker không bị ràng buộc bởi CSP của trang web.

**`backend/app/routes/deepscan.py`** → `audio_extractor.py`:

**`audio_extractor.py`:**
```python
# 1. Tạo tmpdir
tmpdir = tempfile.mkdtemp()
# 2. Download audio với yt-dlp
ydl_opts = {
    'format': 'bestaudio', 
    'outtmpl': f'{tmpdir}/audio.%(ext)s',
    'http_headers': {'User-Agent': 'Mozilla/5.0...'}
}
# (Nếu có ffmpeg, giới hạn tải 300s đầu tiên; nếu không tải toàn bộ)
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=True)
# 3. Kiểm tra kích thước (< 50MB)
# 4. Gọi audio_analyzer.py với file path
# 5. cleanup_audio_tmpdir(tmpdir) — luôn chạy dù thành công hay thất bại
```

**`audio_analyzer.py`:**
```python
client = genai.Client(api_key=gemini_api_key)
# Upload file audio lên Gemini
uploaded_file = await client.aio.files.upload(path=audio_path)
# Gọi Gemini với audio file + prompt
response = await client.aio.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    contents=[uploaded_file, "Tóm tắt video này bằng tiếng Việt, liệt kê điểm chính có mốc thời gian"]
)
```

### Kết quả hiển thị (`ui.js` → `showDeepScanResult()`)
```
🎙️ Deep Scan: {title_vi}
Kênh: {channel}
Thời lượng: {m}:{ss}

Tóm tắt:
{summary}

Các điểm chính (có mốc thời gian):
{key_points}
```

---

## 8. Phân tích trang hiện tại (click icon)

Khi user click vào icon extension trong toolbar:

**`background.js`:**
```javascript
chrome.action.onClicked.addListener(tab => {
    chrome.tabs.sendMessage(tab.id, {type: 'hoverai-analyze-current-page'});
});
```

**`content.js`:**
```javascript
chrome.runtime.onMessage.addListener(msg => {
    if (msg.type === 'hoverai-analyze-current-page') analyzeCurrentPage();
});
```

**`api.js`** → `analyzeCurrentPage()` → `extractCurrentPageContent()`:
```javascript
const html = document.documentElement.outerHTML;  // HTML đã render đầy đủ
return fetchJson('/api/extract-content-from-html', {
    url: window.location.href,
    html,
    page_title: document.title
});
```

Backend nhận HTML đã render (không cần fetch lại) → bỏ qua bước 1 trong content pipeline → thẳng vào Trafilatura/Newspaper.

---

## 9. Kết nối Frontend ↔ Backend

### Cơ chế proxy qua Service Worker

Extension không gọi `http://127.0.0.1:8000` trực tiếp từ content script vì:
1. **CORS**: Browser block cross-origin request đến localhost
2. **CSP**: Các trang web (TikTok, YouTube) có thể chặn

**Giải pháp:** Tất cả API calls đi qua `background.js` (service worker):

```javascript
// content.js / api.js
chrome.runtime.sendMessage({
    type: 'hoverai-api-request',
    path: '/api/extract-content',
    body: { url, gemini_api_key }
}, response => { ... });

// background.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'hoverai-api-request' && ALLOWED_API_PATHS.has(msg.path)) {
        fetch(`http://127.0.0.1:8000${msg.path}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(msg.body)
        }).then(r => r.json()).then(data => sendResponse({ok: true, data}));
        return true; // giữ port mở cho async response
    }
});
```

**Whitelist các path được phép:**
```javascript
const ALLOWED_API_PATHS = new Set([
    '/api/check-url-safety',
    '/api/check-phishing',
    '/api/extract-content',
    '/api/extract-content-from-html'
]);
```

### Timeout

| API | Timeout |
|---|---|
| Security check | `API_TIMEOUT_MS = 4000ms` |
| Content extraction | `CONTENT_API_TIMEOUT_MS = 35000ms` |
| Deep Scan | `DEEPSCAN_TIMEOUT_MS = 200000ms` (3.3 phút) |

### Gemini API Key (BYOK)

Key không được hardcode hay lưu phía server. Flow:
1. User nhập key vào options page → lưu vào `chrome.storage.local`
2. Khi cần gọi AI, `api.js` đọc key từ storage → đưa vào `body` của request
3. Backend nhận key từ `request.body.gemini_api_key`
4. `gemini_client.py` tạo `genai.Client(api_key=key)` per-request

---

## 10. Chi tiết từng file

### Backend

#### `backend/app/main.py`
- Điểm khởi chạy FastAPI
- **Quan trọng:** `load_dotenv()` phải gọi TRƯỚC tất cả project imports
- CORS middleware: `allow_origins=["*"]` (dev), cần thay đổi cho production
- Logging middleware: ghi log mỗi request với thời gian xử lý

#### `backend/app/models/`

| File | Models | Mô tả |
|---|---|---|
| `core.py` | `BaseResponse`, `URLRequest`, `HealthResponse` | Models dùng chung |
| `security.py` | `URLSafetyRequest/Response`, `PhishingRequest/Response` | Bảo mật |
| `content.py` | `ContentExtractionRequest/Response` | Content chung |
| `product.py` | `ProductExtractionResponse` | `price, rating, brand, review_count, extraction_note` |
| `video.py` | `VideoMetadataRequest/Response` | `platform, channel, transcript_language, is_prediction, extraction_note` |

#### `backend/app/routes/`
Routes chỉ là thin HTTP adapters — validate request, delegate đến service, format response. Không có business logic.

| File | Endpoints |
|---|---|
| `security.py` | `POST /api/check-url-safety`, `POST /api/check-phishing` |
| `content.py` | `POST /api/extract-content`, `POST /api/extract-content-from-html` |
| `deepscan.py` | `POST /api/deepscan-audio` |

#### `backend/app/services/core/gemini_client.py`
```python
def call_gemini_sync(api_key: str, prompt: str, model=None) -> str:
    # 1. Khởi tạo Client riêng cho request (BYOK)
    client = genai.Client(api_key=api_key)
    # 2. Thử model chính (gemini-3.5-flash-lite)
    # 3. Nếu lỗi 429/404, fallback sang model phụ (gemini-3.5-flash)
```
Tạo client mới mỗi request. Xử lý fallback tự động khi model bị lỗi quota (429) hoặc không tìm thấy (404), đảm bảo an toàn cho luồng BYOK.

#### `backend/app/services/dispatch/content_classifier.py`
Nhận URL string → trả về `ContentType` enum (`ARTICLE`, `PRODUCT`, `VIDEO`, `UNKNOWN`).
Dùng regex và domain matching, không cần fetch URL.

#### `backend/app/services/dispatch/content_dispatcher.py`
Orchestrator chính của Module 3:
1. Gọi `detect_content_type(url)`
2. Dựa vào ContentType, gọi đúng extractor
3. Gọi đúng summarizer
4. Trả về dict chuẩn hóa

#### `backend/app/services/extractors/jina_reader.py`
Shared Jina Reader client dùng bởi cả article và product extractor.
- `fetch_jina_markdown(url, timeout)` → markdown string
- `parse_title_from_markdown(markdown)` → title string
- `parse_first_paragraph(markdown)` → description string
- **Kỹ thuật:** `httpx.get` sync chạy trong `asyncio.run_in_executor()` để bypass Cloudflare

### Frontend

#### `extension/src/config.js`
```javascript
// Timeouts
const API_TIMEOUT_MS = 4000;
const CONTENT_API_TIMEOUT_MS = 35000;
const DEEPSCAN_TIMEOUT_MS = 200000;

// State
let isAltPressed = false;
let currentVideoUrl = null;       // URL video đang xem, để Deep Scan dùng
let currentLinkData = {...};      // URL + text + domain của link đang hover
let analysisSequence = 0;         // Race condition prevention

// DOM refs (khởi tạo null, ui.js sẽ bind sau khi inject HTML)
let popup, contentStatus, statusIcon, statusText, ...;

// Popup sizing
const POPUP_WIDTH = 480;
const POPUP_HEIGHT = 400;
const PADDING = 12;
```

#### `extension/src/utils.js`
- `extractAndNormalizeURL(anchorElement)` → `{href, domain, isValid}`
  - Lọc bỏ `javascript:`, `mailto:`, `#fragment-only` URLs
- `extractAnchorText(element)` → string text của link
- `calculateSmartPosition(x, y)` → `{left, top}` đảm bảo popup trong viewport

#### `extension/src/api.js`
- `fetchJson(path, body, timeoutMs)` → Promise — gửi qua service worker
- `checkSecurity(linkData)` → `{safety, phishing}` (Promise.all song song)
- `extractTargetLinkContent(linkData)` → content result
- `extractCurrentPageContent()` → lấy DOM hiện tại, gửi `/api/extract-content-from-html`
- `analyzeCurrentPage()` → đặt popup ở giữa màn hình, gọi `extractCurrentPageContent()`

#### `extension/src/ui.js`
- Inject HTML popup template vào `document.body`
- Bind DOM element references (`popup`, `statusIcon`, `chatInput`, v.v.)
- `setLoadingState()` — reset UI về trạng thái loading
- `showSecurityResult({safety, phishing})` — hiển thị kết quả bảo mật
- `showContentResult(result)` — router: gọi show*Result đúng loại
- `showArticleResult(result)` — title + summary
- `showProductResult(result)` — card sản phẩm với price, rating, brand, notes
- `showVideoResult(result)` — video info + transcript status + Deep Scan button logic
- `showDeepScanResult(result)` — kết quả Deep Scan với timestamps
- `showContentError(error, securityResult)` — lỗi trích xuất với hướng dẫn phù hợp
- `showCurrentPageResult(result)` — phân tích trang hiện tại (click icon)

#### `extension/src/content.js`
- Event listeners: `keydown`, `keyup` (Alt tracking)
- `mouseover` → debounce → parse URL → setLoadingState → checkSecurity → showSecurityResult → extractContent → showContentResult
- `mouseout` → clear debounce timer
- `click` ngoài popup → ẩn popup
- `window.blur` → reset `isAltPressed` (khi alt+tab)
- `chrome.runtime.onMessage` → nhận `hoverai-analyze-current-page` từ icon click
- `deepScanBtn.click` → `chrome.runtime.connect()` → long-lived port → Deep Scan
- `handleChat()` → hiện tin nhắn user trong chat (RAG chưa implement)

#### `extension/background.js`
- `chrome.action.onClicked` → forward `hoverai-analyze-current-page` đến tab
- `chrome.runtime.onMessage` → proxy API calls đến localhost:8000
  - Whitelist: 4 paths cụ thể
  - `fetch-shopee-product` → gọi Shopee internal API
  - `fetch-page-html` → fetch HTML trang web với cookies user
- `chrome.runtime.onConnect` → long-lived port cho Deep Scan
  - Nhận `{type:'start-deepscan', url}`
  - Gắn kèm cookies của nền tảng tương ứng (domain-aware cookie cho youtube.com, facebook.com...) gửi qua HTTP header.
  - Fetch `POST /api/deepscan-audio` (30-90s)
  - `port.postMessage({ok, data})` khi xong

---

## Điểm cần lưu ý khi phát triển tiếp

1. **`load_dotenv()` trong main.py** — LUÔN phải ở trước project imports
2. **Jina Reader** — dùng `httpx.get` sync trong executor, không custom User-Agent
3. **Deep Scan** — phải qua `background.js` (CSP bypass), dùng `connect()` (không timeout)
4. **analysisSequence** — counter ngăn race condition khi user hover nhiều link nhanh
5. **is_prediction flag** — UI phải check flag này để hiện cảnh báo đúng + quyết định show Deep Scan button
6. **`ALLOWED_API_PATHS`** trong background.js — thêm vào đây nếu thêm API mới cần proxy
7. **BYOK** — không lưu API key server-side, key đi kèm mỗi request trong body

---

*Tài liệu này mô tả trạng thái code tại commit `4828277` (2026-09-24).*
