# HoverAI - Web Link Analysis & AI Assistant

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-FF6B6B?logo=database&logoColor=white)
![Chrome Extension](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-4285F4?logo=google-chrome&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini%20AI-Powered-FF6F00?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?logo=opensourceinitiative&logoColor=white)

**HoverAI** - An intelligent web link analysis system powered by AI. Simply hold **Alt + Hover** on any link to get instant security checks, content summaries, and AI-powered insights.

## 📋 Table of Contents

- [Features](#-features)
- [Overview](#-overview)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Testing](#-testing)
- [Docker](#-docker)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#️-troubleshooting)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)
- [Acknowledgments](#-acknowledgments)

## ✨ Features

- 🖱️ **Alt + Hover Activation** - Trigger analysis by holding Alt and hovering over any link
- 🛡️ **Security & Phishing Detection** - Google Safe Browsing API + domain mismatch warnings
- 📄 **Smart Content Extraction** - Trafilatura for articles, meta tags for products, transcripts for videos
- 🎯 **Intelligent Summarization** - Gemini AI generates smart summaries (with clickbait warnings)
- 🔊 **Audio Deep Scan** - For videos without transcripts, downloads and analyzes audio with AI
- 🧠 **Contextual Q&A** - Ask questions about content using RAG with ChromaDB & embeddings
- 💾 **Knowledge Base** - Saves all analyzed links and conversations for later review
- 📊 **Dashboard** - Searchable history, filtered by type (news/video/product), with conversation replay
- ⚡ **Streaming Responses** - Real-time AI responses that feel natural and interactive
- 🐳 **Production Ready** - FastAPI async backend, Manifest V3 security standards
- 🔒 **Privacy-First (BYOK)** - Kiến trúc "Bring Your Own Key". Bạn tự quản lý API Key, không tốn phí duy trì server.
- 💾 **100% Local Knowledge Base** - Lịch sử được lưu trực tiếp trên trình duyệt (`chrome.storage.local`). Không theo dõi, không Database bên ngoài.

## 🎯 Overview

**HoverAI** is an intelligent web link analysis assistant that enhances your browsing experience. When you hold **Alt and hover over any link**, HoverAI instantly:

1. **Checks Security** - Verifies if the link is safe using Google Safe Browsing API
2. **Detects Phishing** - Warns if link text domain differs from actual destination
3. **Extracts & Summarizes** - Intelligently extracts content and generates AI summaries:
   - **News articles**: Removes clutter, extracts main text
   - **Product pages**: Extracts prices, specs, ratings via meta tags & JSON-LD
   - **YouTube videos**: Fetches transcripts or predicts summary from title
4. **Deep Scans Audio** - For videos without transcripts, downloads and analyzes audio directly with Gemini AI
5. **Answers Questions** - Ask questions about the content using semantic search (RAG)
6. **Saves History** - Maintains searchable history of all analyzed links and conversations

## 💻 Requirements

- **Python**: 3.8 or higher
- **pip**: Package manager
- **Google Chrome**: Latest version
- **RAM**: Minimum 4GB
- **Disk Space**: ~2GB for dependencies and models
- **API Keys**: 
  - Google Gemini API
  - Google Safe Browsing API

### Optional
- **Docker**: For containerized deployment
- **Docker Compose**: For orchestration

## 🚀 Installation

### 1. Clone Repository

```powershell
git clone https://github.com/Hieu-Techie/HoverAI.git
cd "HoverAI"
```

### 2. Backend Setup

#### Step 1: Create Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### Step 2: Install Dependencies
```powershell
pip install -r backend/requirements.txt
```

#### Step 3: Configure Environment Variables
```powershell
# Copy template
copy .env.example .env

# Edit .env and add your API keys
# HOST=127.0.0.1
# PORT=8000
# SAFE_BROWSING_API_KEY=your_api_key_here
```

#### Step 4: Run Backend Server
```powershell
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

✅ Server running at: `http://127.0.0.1:8000`

### 3. Frontend Setup (Chrome Extension)

#### Step 1: Verify Extension Files
Ensure you have:
- `extension/manifest.json`
- `extension/content.js`
- `extension/styles.css`
- `extension/options.html`
- `extension/options.js`

#### Step 2: Load Extension in Chrome
1. Open Chrome and navigate to: `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top right corner)
3. Click **Load unpacked**
4. Select the `HoverAI/extension/` folder

#### Step 3: Configure API Key (BYOK)
1. Right-click the HoverAI extension icon in your browser toolbar
2. Click **Options**
3. Enter your **Google Gemini API Key** and click Save

#### Step 4: Verify Installation
- Open Chrome DevTools (F12) on any webpage
- Check the Console tab
- You should see: `"HoverAI Extension loaded!"`

## 📖 Usage

### Quick Start

1. **Ensure backend is running** on `http://localhost:8000`
2. **Load extension** in Chrome via `chrome://extensions/` (Developer mode)
3. **Navigate to any webpage**
4. **Hold Alt key + Hover** over any link
5. **See instant results**: Security status, summary, and AI insights

### Feature Walkthrough

#### Security Check (< 1.5s)
- Hover over a link while holding Alt
- Popup shows green ✅ if safe
- Shows red ⚠️ if malicious
- Detects phishing (e.g., "CNN link but goes to Shopee")

#### Content Summary (< 3s)
- **News articles**: Main text extracted, clutter removed
- **Products**: Price, specs, ratings auto-extracted
- **YouTube**: Transcript fetched (if available) or predicted from title (with ⚠️ warning)

#### Deep Scan (Optional)
- For videos without transcripts, click "🔍 Deep Scan"
- Backend downloads audio and sends to Gemini AI
- Get detailed, accurate analysis of what's actually said

#### Ask Questions
- Type a question in the chat area
- AI retrieves relevant sections (RAG) and answers based on actual content
- Responses stream word-by-word for natural interaction

#### Access History
- Click "Lịch sử ↗" (History) button
- Open dashboard to see all analyzed links
- Search by keyword, filter by type
- Replay entire conversations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│       Chrome Extension (Manifest V3)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  UI & Local Storage                              │   │
│  │  - Content Script (Alt+Hover logic)              │   │
│  │  - Options Page (Dashboard & BYOK config)        │   │
│  │  - chrome.storage.local (Knowledge Base)         │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS/HTTP (Gửi URL + API Key)
                       ▼
┌─────────────────────────────────────────────────────────┐
│       FastAPI Backend (Python)                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Core API Endpoints                              │   │
│  │  - Health Check                                  │   │
│  │  - Content Processing                            │   │
│  │  - Safety Verification                           │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AI & RAG Layer                                  │   │
│  │  - Google Gemini Integration                     │   │
│  │  - ChromaDB Vector Store                         │   │
│  │  - Semantic Search                               │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  External APIs                                   │   │
│  │  - Google Gemini API                             │   │
│  │  - Safe Browsing API                             │   │
│  │  - Trafilatura (Web Scraping)                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📚 Tech Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.104.1 | High-performance async web framework |
| Server | Uvicorn | 0.24.0 | ASGI server |
| Data Validation | Pydantic | 2.5.0 | Request/response validation |
| Environment | python-dotenv | 1.0.0 | Environment variable management |
| **AI/LLM** | google-generativeai | 0.3.0 | Google Gemini API integration |
| **Vector DB** | ChromaDB | 0.4.17 | Vector storage for RAG |
| **Embeddings** | sentence-transformers | 2.2.2 | Generate semantic embeddings |
| **Web Scraping** | trafilatura | 1.6.1 | Extract article text |
| **Alternative Scraper** | newspaper3k | 0.9.8 | Fallback article extraction |
| **Video Transcripts** | youtube-transcript-api | 0.6.2 | Fetch YouTube subtitles |
| **Audio Download** | yt-dlp | 2023.12.30 | Download video/audio streams |
| **HTTP Client** | requests | 2.31.0 | Synchronous HTTP calls |
| **Async HTTP** | aiohttp | 3.9.0 | Asynchronous HTTP requests |
| **RAG Framework** | langchain | 0.0.x | Orchestrate RAG pipeline |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Extension | Chrome Extension Manifest V3 | Core browser integration |
| Language | JavaScript (Vanilla) | Logic & Event handling |
| Styling | CSS3 | UI & Popup design |
| Runtime | Chrome Browser Engine | Execution environment |
| Storage | `chrome.storage.local` | Decentralized Knowledge Base |

## 🧪 Testing

### Manual Testing

```powershell
# Test backend endpoints
python -m pytest tests/

# Test extension in Chrome
# Open DevTools and check console logs
```

### Health Checks

```powershell
# Backend health
curl http://127.0.0.1:8000/api/health

# Extension console (F12)
# Should see: "Extension loaded!"
```

## 🐳 Docker

### Build Image

```powershell
docker build -t hoverai:latest .
```

### Run Container

```powershell
docker run --rm \
  -p 8000:8000 \
  -e SAFE_BROWSING_API_KEY=your_key \
  hoverai:latest
```

### Docker Compose

```powershell
docker compose up --build
```

## 📁 Project Structure

```text
HoverAI/
│
├── 📄 .env.example                # Environment variables template (API keys, Config)
├── 📄 .gitignore                  # Git ignore rules
├── 📄 LICENSE                     # MIT License
├── 📄 README.md                   # Documentation (this file)
├── 📄 TASKS.md                    # Module tasks & progress tracker (5 modules)
│
├── 📁 backend/                    # Backend services (Python/FastAPI)
│   ├── 📄 requirements.txt        # Python dependencies
│   └── 📁 app/
│       ├── 📄 __init__.py        # Package initialization
│       ├── 📄 main.py            # FastAPI app & core endpoints
│       ├── 📁 models/            # Pydantic request/response models
│       ├── 📁 routes/            # API endpoint routes
│       │   ├── security.py       # FR2.1, FR2.2 - Safe Browsing & Anti-phishing
│       │   ├── content.py        # FR3.1-3.2 - Content extraction
│       │   ├── video.py          # FR3.3-3.5 - Video & audio processing
│       │   └── rag.py            # FR4.1-4.3 - RAG pipeline
│       ├── 📁 services/          # Business logic
│       │   ├── url_safety.py     # Safe Browsing API wrapper
│       │   ├── phishing_detector.py # Domain comparison
│       │   ├── content_extractor.py # Trafilatura + Newspaper3k
│       │   ├── video_handler.py  # youtube-transcript-api + yt-dlp
│       │   ├── gemini_service.py # Gemini API wrapper
│       │   └── rag_pipeline.py   # LangChain + ChromaDB
│       └── 📁 utils/             # Helper functions
│
└── 📁 extension/                  # Chrome Extension (Manifest V3)
    ├── 📄 manifest.json          # Manifest V3 configuration
    ├── 📄 content.js             # Content script (FR1.1-1.3)
    ├── 📄 styles.css             # Extension styling
    ├── 📄 options.html           # Settings & Local Dashboard UI
    ├── 📄 options.js             # Local Storage & Dashboard logic
    └── 📄 api-client.js          # API communication module
```

## 🔧 Configuration

### Environment Variables (`.env`)

Create `.env` file in root directory:

```env
# Backend Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=False

# API Keys
SAFE_BROWSING_API_KEY=your_safe_browsing_api_key_here

# Database Configuration
CHROMA_PERSIST_DIR=./chromadb_data

# Frontend Configuration
EXTENSION_ID=your_extension_id_here
```

### API Configuration

Edit `backend/app/main.py` for:
- CORS origins
- Middleware settings
- API documentation
- Error handling

## 🛠️ Troubleshooting

### Backend Issues

| Problem | Solution |
|---------|----------|
| Port 8000 already in use | Change port in `.env` or kill process: `netstat -ano \| findstr :8000` |
| Module not found | Activate venv and reinstall: `pip install -r backend/requirements.txt` |
| API key errors | Verify keys in `.env` file and API credentials |
| CORS errors | Check host permissions in extension `manifest.json` |

### Extension Issues

| Problem | Solution |
|---------|----------|
| Extension won't load | Check `manifest.json` syntax and file structure |
| Content script not running | Check console for errors (F12), verify permissions |
| Backend connection fails | Verify backend is running on `localhost:8000` |
| API calls timeout | Increase timeout in `content.js`, check network |

### Common Errors

```
CORS Error: Check chrome://extensions/ permissions
ModuleNotFoundError: pip install missing package
ConnectionError: Start backend: uvicorn app.main:app --reload
```

## 🔐 Security

### Best Practices

✅ **Do:**
- Use `.env` for sensitive data
- Keep API keys in `.env.example` as template
- Enable HTTPS in production
- Validate all user inputs
- Rotate API keys regularly
- Use environment-specific configurations

❌ **Don't:**
- Commit `.env` file with real keys
- Share API keys in code
- Use same keys for dev/prod
- Disable CORS validation
- Store backend secrets in extension (User's personal BYOK keys in local storage are fine)

### HTTPS in Production

```python
# In backend/app/main.py for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Change for production
)
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Steps to Contribute

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add your feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Open Pull Request

### Before Submitting PR

- ✅ Test your changes
- ✅ Follow PEP 8 for Python / ES6 for JavaScript
- ✅ Update documentation
- ✅ Add meaningful commit messages
- ✅ Request review from maintainers

### Current Status

Currently accepting:
- 🐛 Bug reports via Issues
- 💡 Feature suggestions via Discussions
- 📚 Documentation improvements
- 🧪 Testing contributions

## 📝 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) file for complete details.

```
MIT License

Copyright (c) 2026 Hieu-Techie

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 📧 Contact

Have questions or suggestions?

- 📝 **Issues**: [GitHub Issues](https://github.com/Hieu-Techie/HoverAI/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Hieu-Techie/HoverAI/discussions)
- 📧 **Email**: minhhieu04112004@gmail.com
- 🐦 **Twitter**: [@yourhandle](https://twitter.com/yourhandle)

## 🌟 Acknowledgments

### Official Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Web framework
- [Chrome Extension Docs](https://developer.chrome.com/docs/extensions/) - Extension development
- [ChromaDB Docs](https://docs.trychroma.com/) - Vector database
- [Google Generative AI](https://ai.google.dev/) - Gemini API

### Third-party Libraries
- [TensorFlow](https://www.tensorflow.org/) - AI/ML
- [Trafilatura](https://trafilatura.readthedocs.io/) - Web scraping
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video handling
- [Sentence Transformers](https://www.sbert.net/) - Embeddings

### Community
- [Stack Overflow](https://stackoverflow.com/) - Q&A
- [GitHub Community](https://github.com/community) - Support
- [Dev.to](https://dev.to/) - Articles and tutorials

### Tools & Services
- [GitHub](https://github.com/) - Repository hosting
- [Docker Hub](https://hub.docker.com/) - Container registry
- [Google Cloud](https://cloud.google.com/) - API services

---

**Version**: 1.0.0  
**Last Updated**: 2026-08-31  
**Status**: 🚧 Active Development  
**Maintainer**: HoverAI - Web Link Analysis & AI Assistant Team
