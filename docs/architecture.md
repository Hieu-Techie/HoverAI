# HoverAI — Tài liệu Thiết kế Kiến trúc Hệ thống

> **Phiên bản mục tiêu:** 2.0.0 (full 5 modules)  
> **Cập nhật:** 2026-09-25  
> **Trạng thái triển khai:** Module 1–3 ✅ | Module 4–5 ❌ (chưa implement)

---

## 1. Tầm nhìn hệ thống

HoverAI là một **trợ lý duyệt web thông minh** hoạt động hoàn toàn trên máy cục bộ, theo mô hình **Privacy-First / BYOK (Bring Your Own Key)**:

- **Không có server trung tâm** — backend chạy tại `localhost:8000`, dữ liệu không đi ra ngoài
- **Không lưu API key phía backend** — key đi kèm mỗi request từ extension
- **100% local knowledge base** — lịch sử hội thoại lưu trong `chrome.storage.local`
- **Kích hoạt tự nhiên** — Alt + Hover trên bất kỳ link nào

---

## 2. Kiến trúc tổng thể (Target Architecture)

Sơ đồ dưới đây thể hiện **hệ thống đầy đủ theo thiết kế** bao gồm cả các phần chưa implement:

```mermaid
flowchart TD
    subgraph Browser["🌐 Chrome Browser"]
        subgraph Extension["Chrome Extension (Manifest V3)"]
            direction TB
            EventOrchestrator["Event Orchestrator\nAlt+Hover detection\nAnalysis flow control"]
            PopupRenderer["Popup Renderer\nOverlay UI injection\nResult display (all types)"]
            APIClient["API Client\nRequest builder\nService Worker bridge"]
            StateManager["State Manager\nGlobal state & flags\nTimeout constants"]
            URLProcessor["URL Processor\nParsing & validation\nSmart positioning"]
            ServiceWorker["Service Worker ★\nAPI proxy (whitelist)\nDeep Scan long-lived port\nIcon click handler"]
            Dashboard["Dashboard ❌\nHistory list & search\nFilter & export\nAPI Key configuration"]
            LocalStorage["Local Storage ❌\nSessions: URL, title, summary\nConversation history\nTimestamps, content type"]
        end
    end

    subgraph Backend["⚙️ FastAPI Backend (127.0.0.1:8000)"]
        direction TB
        subgraph Routes["Routes — HTTP Adapters"]
            SecurityAPI["Security API\n/api/check-url-safety\n/api/check-phishing"]
            ContentAPI["Content API\n/api/extract-content\n/api/extract-content-from-html\n/api/extract-product\n/api/summarize-from-metadata"]
            DeepScanAPI["Deep Scan API\n/api/deepscan-audio"]
            RAGAPI["RAG API ❌\n/api/rag/add-documents\n/api/rag/query\n/api/rag/ask (SSE)"]
        end

        subgraph Models["Models — Pydantic Validation"]
            CoreModels["Core Models\nBase request/response"]
            SecurityModels["Security Models\nURL Safety, Phishing"]
            ContentModels["Content Models\nArticle, Product, Video"]
            RAGModels["RAG Models ❌\nQuery, Response"]
        end

        subgraph Services["Services — Business Logic"]
            subgraph Sec["Security Services"]
                URLSafety["URL Safety Service\nSafe Browsing API\nTTL Cache 1h"]
                PhishingDetector["Phishing Detector\nDomain mismatch check"]
            end
            subgraph Disp["Dispatch Services"]
                ContentClassifier["Content Classifier\nURL → ContentType\n(VIDEO/PRODUCT/ARTICLE)"]
                ContentDispatcher["Content Dispatcher\nOrchestrate: classify → extract → summarize"]
            end
            subgraph Ext["Extraction Services"]
                ArticleExtractor["Article Extractor\naiohttp → Trafilatura\n→ Newspaper3k → Jina"]
                ProductExtractor["Product Extractor\nJSON-LD → OG → Microdata\n→ H1 → Jina (5 layers)"]
                VideoExtractor["Video Extractor\nYouTube Transcript API\n→ yt-dlp metadata"]
                AudioExtractor["Audio Extractor\nyt-dlp audio download\nTemp file management"]
                JinaClient["Jina Reader Client\nhttpx sync in executor\nCloudflare bypass"]
            end
            subgraph Sum["Summarization Services"]
                ArticleSummarizer["Article Summarizer\nGemini: Vietnamese title\n+ 3 key bullet points"]
                ProductSummarizer["Product Summarizer\nGemini: Vietnamese name\n+ feature highlights"]
                VideoSummarizer["Video Summarizer\nPrompt: transcript\n> description > title-only"]
                AudioAnalyzer["Audio Analyzer\nGemini Files API\nUpload + timestamp analysis"]
            end
            subgraph RAGSvc["RAG Services ❌"]
                TextChunker["Text Chunker\nSplit 512 tokens\n10% overlap"]
                Embedder["Embedder\nsentence-transformers\nall-MiniLM-L6-v2"]
                VectorStore["Vector Store\nChromaDB CRUD\nPersist to disk"]
                RAGPipeline["RAG Pipeline\nRetrieve top-3 chunks\nBuild context prompt"]
                StreamingService["Streaming Service\nServer-Sent Events\nGemini streaming mode"]
            end
            subgraph CoreSvc["Core Services"]
                GeminiClient["Gemini Client\nBYOK per-request client\nEnv var fallback"]
            end
        end
    end

    subgraph External["☁️ External Services"]
        SafeBrowsingAPI["Google Safe Browsing API v4"]
        GeminiAPI["Google Gemini API\n(gemini-2.5-flash)\nText + Audio analysis"]
        JinaReader["Jina Reader\nr.jina.ai\nJS rendering as service"]
        YouTubeTranscript["YouTube Transcript API\n(no API key needed)"]
        YtDlp["yt-dlp\n(local library)\nAudio/video download"]
        ChromaDB["ChromaDB ❌\n(local file storage)\nVector database"]
        SentenceTransformers["sentence-transformers ❌\n(local model)\nall-MiniLM-L6-v2"]
    end

    EventOrchestrator -->|"orchestrate"| APIClient
    EventOrchestrator -->|"render"| PopupRenderer
    APIClient -->|"sendMessage"| ServiceWorker
    ServiceWorker -->|"POST http://127.0.0.1:8000/*"| Routes
    EventOrchestrator -->|"connect('hoverai-deepscan')"| ServiceWorker

    Dashboard <-->|"read/write"| LocalStorage
    EventOrchestrator <-->|"read/write ❌"| LocalStorage

    SecurityAPI --> Sec --> SafeBrowsingAPI
    ContentAPI --> Disp --> Ext
    ContentAPI --> Disp --> Sum --> GeminiClient --> GeminiAPI
    DeepScanAPI --> AudioExtractor --> YtDlp
    DeepScanAPI --> AudioAnalyzer --> GeminiAPI
    RAGAPI -.->|"❌ not yet"| RAGSvc
    ArticleExtractor --> JinaClient --> JinaReader
    ProductExtractor --> JinaClient
    VideoExtractor --> YouTubeTranscript
    RAGSvc -.-> Embedder -.-> SentenceTransformers
    RAGSvc -.-> VectorStore -.-> ChromaDB
```

> **Ký hiệu:** ❌ = chưa implement, ★ = thành phần quan trọng nhất

---

## 3. Phân tầng kiến trúc Backend

```mermaid
flowchart LR
    subgraph T1["Tầng 1: HTTP Layer (Routes)"]
        direction TB
        RA["Security API"]
        RB["Content API"]
        RC["Deep Scan API"]
        RD["RAG API ❌"]
    end

    subgraph T2["Tầng 2: Validation Layer (Models)"]
        direction TB
        MA["Core Models\nBase, Health"]
        MB["Security Models\nURL Safety, Phishing"]
        MC["Content Models\nArticle, Product, Video"]
        MD["RAG Models ❌"]
    end

    subgraph T3["Tầng 3: Business Logic (Services)"]
        direction TB
        GA["Security Services\nURL Safety · Phishing Detector"]
        GB["Dispatch Services\nContent Classifier · Dispatcher"]
        GC["Extraction Services\nArticle · Product · Video · Audio · Jina"]
        GD["Summarization Services\nArticle · Product · Video · Audio Analyzer"]
        GE["RAG Services ❌\nChunker · Embedder · Vector Store · Pipeline · Streaming"]
        GF["Core Services\nGemini Client (BYOK)"]
    end

    T1 -->|"validate request"| T2
    T2 -->|"delegate to services"| T3
    T3 -->|"return Python dict"| T2
    T2 -->|"serialize JSON response"| T1
```

**Nguyên tắc:**
- Routes **không có business logic** — chỉ validate + delegate + HTTP error mapping
- Models đảm bảo **type safety** ở biên (input/output)
- Services **không biết về HTTP** — chỉ nhận/trả Python dict

---

## 4. Sơ đồ 5 Module

```mermaid
flowchart LR
    M1["Module 1 ✅\nUI & Event Handling\nAlt+Hover popup\nSmart positioning"]
    M2["Module 2 ✅\nNetwork Security\nSafe Browsing\nAnti-phishing"]
    M3["Module 3 ✅\nContent Extraction\n& Summarization\nArticle/Product/Video\nDeep Scan Audio"]
    M4["Module 4 ❌\nContextual Q&A\n(RAG Pipeline)\nChromaDB + Embeddings\nStreaming response"]
    M5["Module 5 ❌\nKnowledge Management\nLocal History Storage\nDashboard UI"]

    M1 --> M2 --> M3 --> M4 --> M5

    style M1 fill:#22c55e,color:#fff
    style M2 fill:#22c55e,color:#fff
    style M3 fill:#22c55e,color:#fff
    style M4 fill:#f97316,color:#fff
    style M5 fill:#f97316,color:#fff
```

---

## 5. Frontend Architecture

### 5.1 Load order & responsibilities

```mermaid
flowchart TD
    MF["Extension Manifest\ncontent_scripts load order"]
    MF -->|"1"| C1["State Manager\nGlobal state & flags\nTimeout constants\nDOM refs"]
    C1 -->|"2"| C2["URL Processor\nURL parsing & validation\nAnchor text extraction\nSmart popup positioning"]
    C2 -->|"3"| C3["API Client\nRequest builder via Service Worker\nSecurity check\nContent extraction"]
    C3 -->|"4"| C4["Popup Renderer\nInject overlay HTML\nBind DOM references\nAll result display functions"]
    C4 -->|"5"| C5["Event Orchestrator\nHover / keyboard events\nDeep Scan trigger\nChat message handler"]

    SW["Service Worker\n(loaded separately)"]
    DB["Dashboard ❌\n(loaded on options page only)"]
```

**Lý do chia module thay vì 1 file duy nhất:**
- Mỗi module có trách nhiệm riêng biệt (SRP)
- State Manager và URL Processor không phụ thuộc vào DOM — dùng lại được
- Dễ test từng phần độc lập

### 5.2 State management

Không có framework state — dùng **module-level globals** được khai báo tập trung trong State Manager:

| Biến | Kiểu | Mục đích |
|---|---|---|
| `isAltPressed` | `boolean` | Track phím Alt đang giữ |
| `lastHoveredLink` | `Element` | Tránh trigger lại cùng link |
| `hoverDebounceTimer` | `number` | ID của setTimeout 300ms |
| `analysisSequence` | `number` | Counter ngăn race condition |
| `currentLinkData` | `{href, text, domain}` | Dữ liệu link đang phân tích |
| `currentVideoUrl` | `string\|null` | URL video cho Deep Scan |
| `popup, statusIcon, ...` | `Element` | DOM refs (bind bởi Popup Renderer) |

### 5.3 Service Worker — Proxy Architecture

```mermaid
flowchart TD
    CLICK["Extension Icon Click"] -->|"forward message"| TAB["Content script\nin active tab"]

    MSG["Incoming Message\nfrom content script"] --> WL{"Path in whitelist?\n/api/check-url-safety\n/api/check-phishing\n/api/extract-content\n/api/extract-content-from-html"}
    WL -->|"✅ allowed"| FETCH["fetch to localhost:8000\nKeep port open for async response"]
    WL -->|"❌ not allowed"| REJECT["Reject immediately\n(port closes)"]

    CONN["Long-lived Port Connection\n(Deep Scan channel)"] --> PORT["Receive start-deepscan event\nFetch POST /api/deepscan-audio\nRespond with result when done"]
```

> **Tại sao Deep Scan dùng long-lived port thay vì message?**  
> Short message → port tự đóng sau ~5 phút chờ. Deep Scan mất 30–90s → cần long-lived port.  
> Fetch trực tiếp từ content script → TikTok/YouTube CSP chặn kết nối đến localhost.  
> → Service Worker không bị CSP của trang web → có thể fetch localhost tự do.

---

## 6. Content Processing Pipeline (Module 3)

### 6.1 Content Type Detection

```mermaid
flowchart TD
    URL["URL input"] --> P["URL Parser"]
    P --> V{"Video platform?\nyoutube.com, youtu.be\ntiktok.com, vimeo.com\nfacebook.com, twitter.com\nbilibili.com ..."}
    V -->|"✅"| VID["ContentType: VIDEO"]
    V -->|"❌"| PM{"Known product path?\n/product/, /dp/\n/item/, /p/, /pd/"}
    PM -->|"✅"| PROD["ContentType: PRODUCT"]
    PM -->|"❌"| EC{"E-commerce domain?\nshopee.vn, tiki.vn\namazon.com, lazada.vn\n+ path heuristic"}
    EC -->|"✅ + product-like path"| PROD
    EC -->|"❌"| SD{"HTML has structured data?\nJSON-LD @type=Product\nog:type=product"}
    SD -->|"✅"| PROD
    SD -->|"❌"| ART["ContentType: ARTICLE (default)"]
```

### 6.2 Article Extraction Pipeline

```mermaid
flowchart TD
    URL["URL"] --> FE["HTML Fetcher\naiohttp, Chrome User-Agent\nTimeout 10s, Max 5MB"]
    FE -->|"Bot challenge / Error"| JINA
    FE -->|"HTML OK"| BC{"Bot challenge detected?\nCloudflare / CAPTCHA"}
    BC -->|"Yes"| JINA
    BC -->|"No"| TR["Trafilatura\nPrecision mode\nBoilerplate removal"]
    TR -->|"< 80 chars / None"| NP["Newspaper3k\nFallback extractor"]
    TR -->|"OK"| LQ{"Low quality check\ntext < 300 chars AND\nnav ratio > 50%"}
    NP -->|"OK"| LQ
    NP -->|"Fail"| JINA
    LQ -->|"Low quality"| JINA
    LQ -->|"OK"| AS["Article Summarizer\nGemini: Vietnamese title\n+ 3 objective bullet points"]
    JINA["Jina Reader Client\nhttpx sync in executor\nr.jina.ai/{url}\nNo custom User-Agent"] -->|"OK"| AS
    JINA -->|"Fail"| ERR["Extraction Error\nCONTENT_NOT_FOUND"]
    AS --> OUT["Response\ncontent_type: article\ntitle, summary, metadata"]
```

### 6.3 Product Extraction Pipeline (5 Layers)

```mermaid
flowchart TD
    URL["URL"] --> FETCH["HTML Fetcher"]
    FETCH --> L1["Layer 1: JSON-LD\nschema.org Product/Offer\nMost reliable standard"]
    L1 -->|"Missing data"| L2["Layer 2: Open Graph\nog:title, og:price\nFacebook protocol"]
    L2 -->|"Missing data"| L3["Layer 3: Microdata\nitemtype=schema.org/Product\nHTML5 microdata"]
    L3 -->|"Missing data"| L4["Layer 4: H1 + Meta tags\nHeading as product name\nmeta price/description"]
    L4 -->|"Missing data"| L5["Layer 5: Jina Reader\nJS-rendered page\nParse title/desc from markdown"]

    L1 --> PS
    L2 --> PS
    L3 --> PS
    L4 --> PS
    L5 --> PS

    PS["Product Summarizer\nGemini: Vietnamese name\n+ feature highlights\nextraction_note in metadata"]
    PS --> OUT["Response\ncontent_type: product\ntitle, price, rating, brand\nextraction_note, summary"]
```

### 6.4 Video Processing Pipeline

```mermaid
flowchart TD
    URL["URL"] --> CLS["Content Classifier"]
    CLS -->|"YouTube"| YT["Video Extractor — YouTube"]
    CLS -->|"TikTok / Vimeo / Other"| OT["Video Extractor — Other Platforms"]

    YT --> TR["YouTube Transcript API\nPriority: vi → en → en-US → auto-generated"]
    TR -->|"Transcript found"| VS1["Video Summarizer\nSummarize from transcript\nis_prediction=False"]
    TR -->|"Disabled / Not found / Error"| META["yt-dlp\nMetadata only mode\ntitle, description, channel"]
    META -->|"Has description"| VS2["Video Summarizer\nSummarize from description\nis_prediction=True"]
    META -->|"Title only"| VS3["Video Summarizer\nPredict from title only\nis_prediction=True"]

    OT --> ODLP["yt-dlp\ntitle, description\nchannel, duration, thumbnail"]
    ODLP --> VS4["Video Summarizer\nSummarize from description\nis_prediction=True\nnote=TRANSCRIPT_NOT_AVAILABLE"]

    VS1 --> OUT["Response\ncontent_type: video\ntitle, summary\nmetadata: {platform, channel\ntranscript_language\nis_prediction, extraction_note}"]
    VS2 --> OUT
    VS3 --> OUT
    VS4 --> OUT
```

### 6.5 Deep Scan Audio Pipeline (FR3.5)

```mermaid
sequenceDiagram
    participant C as Event Orchestrator
    participant B as Service Worker
    participant D as Deep Scan API
    participant AE as Audio Extractor
    participant AA as Audio Analyzer
    participant GM as Gemini Files API

    C->>B: Open long-lived port (hoverai-deepscan)
    C->>B: Send {start-deepscan, url}
    Note over B: No page CSP — can fetch localhost freely
    B->>D: POST /api/deepscan-audio {url, api_key}
    D->>AE: Download audio [timeout 120s]
    AE->>AE: yt-dlp extract & download
    AE->>AE: Validate size < 50MB
    AE-->>D: (audio_path, video_info)
    D->>AA: Analyze audio file
    AA->>GM: Upload audio file (MIME type auto-detected)
    GM-->>AA: file_ref (PROCESSING state)
    AA->>AA: Poll until ACTIVE (max 60s)
    AA->>GM: Generate content (audio + prompt)
    GM-->>AA: Raw analysis text
    AA->>GM: Delete uploaded file (cleanup)
    AA-->>D: {title_vi, summary, key_points}
    D->>AE: Cleanup temp directory
    D-->>B: HTTP 200 JSON
    B->>C: Port message {ok:true, data}
    C->>C: Render Deep Scan result
```

---

## 7. RAG Pipeline Architecture (Module 4 — Chưa implement)

```mermaid
flowchart TD
    subgraph Ingest["Ingestion Flow — khi phân tích link mới"]
        TXT["Extracted Text\n(Article / Product / Video)"] --> CHK["Text Chunker\nSplit into 512-token chunks\n10% overlap between chunks"]
        CHK --> EMB["Embedder\nsentence-transformers\nall-MiniLM-L6-v2 (384-dim)"]
        EMB --> VS["Vector Store\nChromaDB\nStore vectors + metadata\n(url, title, chunk_index)"]
    end

    subgraph Query["Query Flow — khi user gửi câu hỏi"]
        Q["User Question"] --> QEMB["Embedder\nConvert question to vector"]
        QEMB --> SRC["Vector Store\nCosine similarity search\nRetrieve top-3 relevant chunks"]
        SRC --> CTX["RAG Pipeline\nBuild prompt:\nSystem context + chunks + question"]
        CTX --> GEM["Gemini Client\nStreaming generation mode"]
        GEM --> SSE["Streaming Service\nServer-Sent Events\n/api/rag/ask endpoint"]
        SSE -->|"word-by-word stream"| UI["Popup Chat UI"]
    end
```

**Thiết kế ChromaDB:**
```
Collection: "hoverai_kb"
Document metadata:
  - url: string          # URL gốc của trang
  - title: string        # Tiêu đề trang
  - content_type: string # article | product | video
  - chunk_index: int     # Vị trí chunk trong tài liệu
  - created_at: timestamp
```

**Embedding model:** `all-MiniLM-L6-v2` — 384 chiều, chạy local, nhỏ (~80MB), tốt cho tiếng Anh và có hỗ trợ tiếng Việt cơ bản.

---

## 8. Knowledge Management Architecture (Module 5 — Chưa implement)

```mermaid
flowchart TD
    subgraph LocalStorage["chrome.storage.local (Browser-side)"]
        SESS["Sessions\n{id, url, title, content_type\nsummary, timestamp}"]
        CONV["Conversations\n{session_id, messages[]\n{role, content, timestamp}}"]
    end

    subgraph ExtensionLayer["Extension"]
        ORCH["Event Orchestrator\nAuto-save after each analysis"]
        DASH["Dashboard\nOptions page UI"]
    end

    subgraph DashFeatures["Dashboard Features"]
        LIST["Session List\nWith content type icons"]
        SRCH["Local Keyword Search"]
        FILT["Filter by date / type"]
        VIEW["Conversation Viewer\nFull replay"]
        EXP["Export JSON / PDF"]
        DEL["Delete session"]
        APIKEY["Gemini API Key Setup\n(BYOK configuration)"]
    end

    ORCH -->|"write"| LocalStorage
    DASH -->|"read"| LocalStorage
    DASH --> LIST
    DASH --> SRCH
    DASH --> FILT
    DASH --> VIEW
    DASH --> EXP
    DASH --> DEL
    DASH --> APIKEY
```

**Schema lưu trữ dự kiến:**
```javascript
// chrome.storage.local key: "hoverai_sessions"
[
  {
    id: "uuid-v4",
    url: "https://...",
    title: "Tiêu đề trang",
    content_type: "article" | "product" | "video",
    summary: "...",
    timestamp: 1234567890,
    messages: [
      { role: "user", content: "Câu hỏi...", timestamp: ... },
      { role: "ai",   content: "Trả lời...", timestamp: ... }
    ]
  }
]
```

---

## 9. Security Architecture

### 9.1 URL Safety Check

```mermaid
flowchart TD
    REQ["POST /api/check-url-safety\n{url}"] --> CACHE{"TTL Cache hit?\n(1000 URLs, TTL 1h)"}
    CACHE -->|"Hit"| RET["Return cached result"]
    CACHE -->|"Miss"| KEY{"API Key configured?"}
    KEY -->|"No"| MISS["{safe:False\nthreat_type:API_KEY_MISSING}"]
    KEY -->|"Yes"| SB["Google Safe Browsing API\nv4/threatMatches:find\nCheck: MALWARE, SOCIAL_ENGINEERING\nUNWANTED_SOFTWARE"]
    SB -->|"Match found"| DANGER["{safe:False, threat_type: MALWARE/...}"]
    SB -->|"No match"| SAFE["{safe:True, threat_type: SAFE}"]
    SB -->|"Timeout / Error"| ERR["{safe:True, threat_type: TIMEOUT}"]
    SAFE --> STORE["Store in TTL Cache"]
    DANGER --> STORE
```

> `API_KEY_MISSING` → `safe:False` nhưng UI kiểm tra danh sách `cannotVerify` → hiện ⚠️ "Không thể xác minh" (không block user)

### 9.2 BYOK Security Flow

```mermaid
flowchart LR
    USER["User\nEnter Gemini API Key\nin Dashboard ❌"] -->|"write"| LS["Local Storage\ngemini_api_key"]
    LS -->|"read when needed"| API["API Client\nKey included in request body"]
    API -->|"HTTP body (not header)"| BE["Gemini Client\nCreate per-request client"]
    BE -->|"genai.Client(api_key=key)"| GM["Gemini API"]

    ENV[".env file\nGEMINI_API_KEY"] -.->|"fallback if\nno user key"| BE
```

**Không có API key nào được:**
- Hardcode trong source code
- Lưu trong database phía server
- Ghi vào log file

---

## 10. API Endpoints — Full Reference

### Hiện có (Module 1–3)

| Method | Path | Request Body | Response | Module |
|--------|------|-------------|---------|--------|
| `GET` | `/api/health` | — | `{status, service, version}` | Core |
| `POST` | `/api/check-url-safety` | `{url}` | `{safe, threat_type}` | FR2.1 |
| `POST` | `/api/check-phishing` | `{href_url, anchor_text}` | `{is_phishing, mismatch_warning}` | FR2.2 |
| `POST` | `/api/extract-content` | `{url, gemini_api_key?}` | `ContentExtractionResponse` | FR3.1/3.2/3.3 |
| `POST` | `/api/extract-content-from-html` | `{url, html, page_title, gemini_api_key?}` | `ContentExtractionResponse` | FR3.1/3.2/3.3 |
| `POST` | `/api/extract-product` | `{url, html?, gemini_api_key?}` | `ProductExtractionResponse` | FR3.2 |
| `POST` | `/api/summarize-from-metadata` | `{title, description?, channel?, platform?, gemini_api_key?}` | `VideoMetadataResponse` | FR3.4 |
| `POST` | `/api/deepscan-audio` | `{url, gemini_api_key?}` | `DeepScanResponse` | FR3.5 |

### Kế hoạch (Module 4 — RAG)

| Method | Path | Request Body | Response | Module |
|--------|------|-------------|---------|--------|
| `POST` | `/api/rag/add-documents` | `{url, text, title, content_type, gemini_api_key?}` | `{chunks_added, collection_size}` | FR4.1 |
| `POST` | `/api/rag/query` | `{question, url?}` | `{chunks: [{text, score, metadata}]}` | FR4.2 |
| `POST` | `/api/rag/ask` | `{question, context_url?, gemini_api_key?}` | `SSE stream: text/event-stream` | FR4.3 |

### ContentExtractionResponse schema

```json
{
  "url": "string",
  "content_type": "article | product | video",
  "title": "string (Vietnamese if AI-normalized)",
  "text": "string (raw extracted text)",
  "summary": "string | null",
  "metadata": {
    "author": "string | null",
    "date": "string | null",
    "site_name": "string | null",
    "price": "number | null",
    "price_display": "string | null",
    "currency": "string | null",
    "rating": "number | null",
    "brand": "string | null",
    "review_count": "string | null",
    "extraction_note": "SPA_PARTIAL | JINA_PARTIAL | PRICE_NOT_AVAILABLE | TRANSCRIPT_DISABLED | TRANSCRIPT_NOT_FOUND | TRANSCRIPT_ERROR | TRANSCRIPT_NOT_AVAILABLE | null",
    "platform": "YouTube | TikTok | Vimeo | ...",
    "channel": "string | null",
    "transcript_language": "vi | en | null",
    "is_auto_generated": "boolean",
    "is_prediction": "boolean"
  }
}
```

---

## 11. Dependency & Tech Stack

### Backend

| Thư viện | Phiên bản | Mục đích | Module |
|---|---|---|---|
| `fastapi` | 0.104+ | Async web framework | Core |
| `uvicorn` | 0.24+ | ASGI server | Core |
| `pydantic` | 2.5+ | Validation & serialization | Core |
| `python-dotenv` | 1.0+ | Environment variable management | Core |
| `aiohttp` | 3.9+ | Async HTTP client (HTML fetching) | M3 |
| `httpx` | 0.27+ | Sync HTTP client (Jina Reader) | M3 |
| `trafilatura` | 1.6+ | Article text extraction | FR3.1 |
| `newspaper3k` | 0.9+ | Article extraction fallback | FR3.1 |
| `beautifulsoup4` | 4.12+ | HTML parsing (product extraction) | FR3.2 |
| `youtube-transcript-api` | 0.6+ | YouTube subtitle fetching | FR3.3 |
| `yt-dlp` | latest | Audio/video download | FR3.5 |
| `google-genai` | latest | Gemini API client | M3, M4 |
| `cachetools` | 5.3+ | TTL cache (Safe Browsing results) | FR2.1 |
| `sentence-transformers` | 2.2+ | Local text embeddings | FR4.1 ❌ |
| `chromadb` | 0.4+ | Local vector database | FR4.1 ❌ |

### Frontend

| Công nghệ | Mục đích |
|---|---|
| Chrome Extension Manifest V3 | Extension platform |
| JavaScript (Vanilla ES6+) | No bundler/framework needed |
| CSS3 | Popup styling |
| `chrome.storage.local` | Decentralized local history (M5 ❌) |
| `chrome.runtime.connect()` | Long-lived port for Deep Scan |
| `chrome.runtime.sendMessage()` | Standard short API calls |

---

## 12. Deployment Architecture

```mermaid
flowchart LR
    subgraph Local["Máy người dùng (Local Only)"]
        PY["FastAPI Backend\nlocalhost:8000"]
        CR["Chrome Browser\nExtension installed"]
        DB["Vector Database ❌\n(ChromaDB local files)"]
        ENV["API Keys\n(.env file)"]
    end

    subgraph Cloud["Cloud (External APIs Only)"]
        SB["Google Safe Browsing API"]
        GM["Google Gemini API"]
        JN["Jina Reader (r.jina.ai)"]
    end

    CR <-->|"localhost:8000 / HTTP+CORS"| PY
    PY --> ENV
    PY <-->|"HTTPS"| SB
    PY <-->|"HTTPS"| GM
    PY <-->|"HTTPS"| JN
    PY <-->|"Local disk I/O"| DB
```

**Không có:**
- Cloud database
- User authentication / accounts
- Server-side session storage
- Analytics / telemetry

---

## 13. Design Decisions & Tradeoffs

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Extension vs Web app | Chrome Extension | Cần truy cập DOM, chạy trên mọi trang |
| Backend framework | FastAPI | Async native, auto OpenAPI docs, Pydantic validation |
| AI model | Gemini 2.5 Flash | Nhanh, hỗ trợ audio file, giá tốt, đa ngôn ngữ |
| Article extractor chính | Trafilatura | Tốt nhất cho news articles, loại boilerplate giỏi |
| HTTP client cho Jina | httpx sync in executor | aiohttp và httpx async bị Cloudflare block; sync qua được |
| Vector DB | ChromaDB | Chạy local, không cần server riêng, persistent |
| Embedding model | all-MiniLM-L6-v2 | ~80MB, fast inference, đủ tốt cho tiếng Việt |
| Deep Scan transport | Long-lived port (connect) | Short message timeout 5 phút; page CSP block fetch to localhost |
| API key management | BYOK per-request | Không lưu key phía server, privacy-first |
| Knowledge base | chrome.storage.local | Fully decentralized, no tracking, no backend dependency |

---

*Tài liệu này mô tả thiết kế đích của hệ thống HoverAI (5 modules). Các phần đánh dấu ❌ là kế hoạch thiết kế chưa được triển khai.*
