# HoverAI - Hệ thống Phân tích, Tóm tắt & Tương tác Liên kết Web tích hợp AI

## 📋 Tracking Progress

This document tracks the development progress of HoverAI project across 5 main modules based on functional requirements (FR).

---

## Module 1: Giao diện & Bắt sự kiện (UI & Event Handling) 🖱️

Xây dựng giao diện popup và logic bắt sự kiện Alt + Hover trên liên kết.

### FR1.1 - Kích hoạt có điều kiện (Conditional Activation)
- [x] Setup content.js để lắng nghe sự kiện keyboard (Alt key) - *Lắng nghe phím Alt* ✅
- [x] Implement hover detection on links - *Phát hiện khi di chuột vào liên kết* ✅
- [x] Create mock popup UI - *Tạo giao diện popup mẫu* ✅
- [x] Combine Alt + Hover event (Alt AND mouseover together) - *Kích hoạt khi cùng lúc Alt + Hover* ✅
- [x] Store hover state in memory for debouncing - *Lưu trạng thái để tránh gọi API liên tục* ✅

### FR1.2 - Thu thập URL chính xác (URL Extraction)
- [x] Extract href attribute from link element - *Bóc tách thuộc tính href từ liên kết* ✅
- [x] Validate and normalize URLs - *Kiểm tra và chuẩn hóa URL* ✅
- [x] Extract link text (anchor text) for phishing detection - *Lấy text hiển thị để phát hiện lừa đảo* ✅
- [x] Handle edge cases (relative URLs, anchors) - *Xử lý các trường hợp đặc biệt* ✅

### FR1.3 - Tự động căn chỉnh UI Popup (Smart Positioning)
- [x] Calculate mouse position relative to viewport - *Tính toán tọa độ chuột* ✅
- [x] Get screen/window dimensions - *Lấy kích thước màn hình* ✅
- [x] Implement auto-flip left/right logic - *Tự động lật trái/phải* ✅
- [x] Implement auto-flip top/bottom logic - *Tự động lật trên/dưới* ✅
- [x] Ensure popup never overflows screen boundary - *Đảm bảo popup không tràn ngoài màn hình* ✅
- [x] Add padding/margin to keep popup visible - *Thêm khoảng cách an toàn* ✅

**Status**: 100% Complete (15/15 tasks)

---

## Module 2: An ninh Mạng (Network Security) 🛡️

Kiểm tra URL an toàn và phát hiện lừa đảo.

### FR2.1 - Kiểm tra mã độc (Malware Detection via Safe Browsing)
- [x] Create Safe Browsing API integration module - *Tạo module gọi Google Safe Browsing API* ✅
- [x] Implement POST /api/check-url-safety endpoint - *Tạo endpoint kiểm tra URL* ✅
- [x] Send URL to Google Safe Browsing API - *Gửi URL lên Safe Browsing* ✅
- [x] Handle API responses (SAFE / DANGEROUS) - *Xử lý kết quả từ API* ✅
- [x] Implement caching for repeated URLs (in-memory) - *Cache kết quả để tránh gọi API lại* ✅
- [x] Return safety status with threat type - *Trả về kết quả với loại mối đe dọa* ✅
- [x] Add timeout handling (max 1.5 seconds) - *Xử lý timeout (< 1.5s)* ✅
- [x] Test with known malicious URLs - *Kiểm tra với các URL độc hại nổi tiếng* ✅

### FR2.2 - Phát hiện ngụy trang (Anti-Phishing Detection)
- [x] Extract domain from anchor text - *Bóc tách domain từ text liên kết* ✅
- [x] Extract domain from href URL - *Bóc tách domain từ URL đích* ✅
- [x] Implement domain comparison logic - *So sánh hai domain* ✅
- [x] Create POST /api/check-phishing endpoint - *Tạo endpoint phát hiện lừa đảo* ✅
- [x] Return mismatch warning if domains differ - *Cảnh báo nếu domain không khớp* ✅
- [x] Handle subdomain variations (youtube.com vs m.youtube.com) - *Xử lý subdomain* ✅
- [x] Add known domain mapping (common aliasing) - *Ánh xạ domain nổi tiếng* ✅

**Status**: 100% Complete (15/15 tasks)

---

## Module 3: Trích xuất, Tóm tắt & Phân loại Dữ liệu (Content Extraction & Summarization) 📄

Xử lý các loại content khác nhau và tạo tóm tắt thông minh.

### FR3.1 - Xử lý Báo chí/Web thông tin (News & Articles)
- [x] Create content extraction module using Trafilatura - *Tạo module bóc tách nội dung* ✅
- [x] Implement POST /api/extract-content endpoint - *Tạo endpoint trích xuất* ✅
- [x] Remove boilerplate (menu, footer, ads) - *Loại bỏ menu, footer, quảng cáo* ✅
- [x] Extract main article text - *Bóc tách text bài viết chính* ✅
- [x] Extract article title and metadata - *Lấy tiêu đề và metadata* ✅
- [x] Fallback to newspaper3k if Trafilatura fails - *Dự phòng bằng newspaper3k* ✅
- [x] Create AI summarization service with Gemini API (BYOK) - *Tạo service gọi Gemini tóm tắt* ✅
- [x] Design standard 3-bullet prompt for articles - *Thiết kế prompt tóm tắt 3 ý chính khách quan* ✅
- [x] Integrate summarizer into content pipeline - *Nối luồng: Bóc tách text -> Gemini tóm tắt -> Trả về Popup* ✅

### FR3.2 - Xử lý Trang Sản phẩm (Product Pages & Structured Data)
- [x] Create meta tag parser (OpenGraph, Schema.org) - *Phân tích meta tag và Schema.org* ✅
- [x] Extract product name from JSON-LD or meta tags - *Lấy tên sản phẩm* ✅
- [x] Extract price, ratings, specifications - *Lấy giá, đánh giá, thông số* ✅
- [x] Parse structured data from HTML - *Phân tích dữ liệu có cấu trúc* ✅
- [x] Create POST /api/extract-product endpoint - *Tạo endpoint trích xuất sản phẩm* ✅
- [x] Handle different e-commerce sites (Amazon, Shopee, etc) - *Xử lý các site khác nhau* ✅

### FR3.3 - Xử lý Video & Lấy Phụ đề (Video Transcript Extraction)
- [ ] Create YouTube transcript extraction module - *Tạo module lấy phụ đề YouTube*
- [ ] Use youtube-transcript-api to fetch transcripts - *Dùng youtube-transcript-api*
- [ ] Create POST /api/extract-transcript endpoint - *Tạo endpoint lấy transcript*
- [ ] Handle videos without transcripts - *Xử lý video không có phụ đề*
- [ ] Return transcript text to Gemini for summarization - *Gửi text cho Gemini tóm tắt*

### FR3.4 - Tóm tắt với cảnh báo Clickbait (Fallback Summarization with Warning)
- [ ] Extract video title and description - *Lấy tiêu đề và mô tả video*
- [ ] Create POST /api/summarize-from-metadata endpoint - *Tạo endpoint tóm tắt từ metadata*
- [ ] Send title+description to Gemini for prediction summary - *Gửi cho Gemini tóm tắt dự đoán*
- [ ] Add ⚠️ warning label (Dự đoán từ tiêu đề, có thể chứa yếu tố giật gân) - *Thêm cảnh báo về clickbait*
- [ ] Include "Deep Scan" button recommendation - *Gợi ý nút Deep Scan*
- [ ] Test with clickbait videos - *Kiểm tra với video giật gân*

### FR3.5 - Quét sâu Âm thanh (Deep Scan Audio Analysis)
- [ ] Implement yt-dlp integration for audio download - *Tích hợp yt-dlp để tải âm thanh*
- [ ] Download audio stream from YouTube - *Tải luồng âm thanh*
- [ ] Convert audio to format acceptable by Gemini - *Chuyển đổi định dạng audio*
- [ ] Create POST /api/deepscan-audio endpoint - *Tạo endpoint deep scan*
- [ ] Send audio directly to Gemini API for analysis - *Gửi audio cho Gemini phân tích*
- [ ] Extract timestamps and key points from audio - *Trích xuất mốc thời gian*
- [ ] Return detailed transcription + analysis - *Trả về transcription chi tiết*
- [ ] Handle audio-only streams and podcasts - *Xử lý stream audio và podcast*
- [ ] Add timeout for large audio files (max 5 mins) - *Xử lý timeout*

**Status**: 43% Complete (15/35 tasks) — FR3.1 ✅ FR3.2 ✅

---

## Module 4: Hỏi đáp Ngữ cảnh (Contextual Q&A with RAG) 💬

Triển khai RAG pipeline để trả lời câu hỏi dựa trên content.

### FR4.1 - Phân mảnh & Mã hóa (Chunking & Embedding)
- [ ] Create text chunking module (max 512 tokens per chunk) - *Chia text thành chunks*
- [ ] Implement overlap between chunks (10% overlap) - *Tạo overlap giữa chunks*
- [ ] Use sentence-transformers to generate embeddings - *Tạo embedding bằng sentence-transformers*
- [ ] Store embeddings in ChromaDB with metadata - *Lưu embedding vào ChromaDB*
- [ ] Create POST /api/rag/add-documents endpoint - *Tạo endpoint thêm tài liệu*
- [ ] Add document metadata (URL, title, source) - *Thêm metadata tài liệu*
- [ ] Handle large documents (split into multiple chunks) - *Xử lý tài liệu lớn*

### FR4.2 - Tìm kiếm Ngữ nghĩa (Semantic Search)
- [ ] Convert user question to embedding - *Chuyển câu hỏi thành embedding*
- [ ] Query ChromaDB for similar chunks - *Tìm chunks tương tự*
- [ ] Retrieve top 3 relevant chunks - *Lấy 3 chunk liên quan nhất*
- [ ] Calculate and return relevance scores - *Tính điểm liên quan*
- [ ] Create POST /api/rag/query endpoint - *Tạo endpoint truy vấn*
- [ ] Validate input question (non-empty, valid) - *Kiểm tra input*

### FR4.3 - Luồng trực tiếp (Streaming Response)
- [ ] Configure Gemini API to use streaming mode - *Cấu hình Gemini streaming*
- [ ] Send context chunks + user question to Gemini - *Gửi context + câu hỏi*
- [ ] Implement Server-Sent Events (SSE) for streaming - *Triển khai SSE cho streaming*
- [ ] Create POST /api/rag/ask endpoint (streaming) - *Tạo endpoint streaming*
- [ ] Return response word-by-word in real-time - *Trả về response từng từ*
- [ ] Add token counter to prevent overflow - *Đếm token để tránh overflow*
- [ ] Handle connection drops gracefully - *Xử lý khi kết nối bị mất*

**Status**: 0% Complete (0/21 tasks)

---

## Module 5: Quản lý Tri thức (Knowledge Management) 📚

Lưu trữ lịch sử và cung cấp dashboard quản lý trực tiếp trên trình duyệt (Decentralized).

### FR5.1 - Ghi nhận Phiên làm việc (Local Session Tracking)
- [ ] Implement Chrome Local Storage integration (`chrome.storage.local`) - *Lưu trữ cục bộ trên trình duyệt*
- [ ] Create storage schema for sessions - *Tạo cấu trúc dữ liệu lưu trữ*
- [ ] Store URL, title, and summary locally - *Lưu URL, tiêu đề, tóm tắt*
- [ ] Store full conversation history locally (user questions + AI replies) - *Lưu lịch sử hội thoại*
- [ ] Auto-save on first interaction - *Tự động lưu lần đầu tiên*
- [ ] Update local session with new messages - *Cập nhật khi có tin nhắn mới*
- [ ] Add timestamp for each interaction - *Thêm timestamp*
- [ ] Implement storage quota management - *Quản lý dung lượng lưu trữ (xóa phiên cũ nếu đầy)*

### FR5.2 - Giao diện Dashboard (Extension Options Page)
- [ ] Create options.html (standalone Extension page) - *Tạo trang cài đặt của Extension*
- [ ] List all visited links with thumbnails from local storage - *Liệt kê tất cả liên kết*
- [ ] Implement local search by keyword - *Tìm kiếm theo từ khóa cục bộ*
- [ ] Display full conversation for each link - *Hiển thị cuộc hội thoại*
- [ ] Add filters (by date, by type - news/video/product) - *Thêm bộ lọc*
- [ ] Export conversation to JSON/PDF - *Xuất conversation*
- [ ] Delete individual sessions - *Xóa phiên làm việc*
- [ ] Add API Key configuration UI - *Thêm giao diện để người dùng nhập Gemini API Key*

**Status**: 0% Complete (0/16 tasks)

---

## 📊 Overall Project Summary

| Module | Name | Completion | Tasks | Status |
|--------|------|-----------|-------|--------|
| 1 | UI & Event Handling | 100% ✅ | 15/15 | 🎉 **COMPLETE** |
| 2 | Network Security | 100% ✅ | 15/15 | 🎉 **COMPLETE** |
| 3 | Content Extraction & Summarization | 43% | 15/35 | 🚧 FR3.1 ✅ FR3.2 ✅ |
| 4 | Contextual Q&A (RAG) | 0% | 0/21 | ❌ Requires Module 3 |
| 5 | Knowledge Management | 0% | 0/16 | ❌ Requires Module 4 |
| **TOTAL** | **HoverAI Project** | **44%** 🚧 | **45/102** | Continue Module 3 |

---

## 📌 Priority Tasks (Next Steps)

### 🟡 **NEXT - Module 3**
1. **[Module 3.1]** Setup content extraction module using Trafilatura
   - File: `backend/app/services/content_extractor.py`
2. **[Module 3.2]** Create meta tag parser for product pages

---

## 📚 Documentation Files

- **[TASKS.md](TASKS.md)** - This file: 102 tasks across 5 Modules
- **[README.md](README.md)** - Full project overview & architecture
