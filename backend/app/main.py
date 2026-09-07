import os
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, HttpUrl
from typing import Optional, Any
from dotenv import load_dotenv
from app.routes import security

load_dotenv()

class Settings:
    SAFE_BROWSING_API_KEY: str = os.getenv("SAFE_BROWSING_API_KEY", "")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SmartWebAI")

class BaseResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None

class URLRequest(BaseModel):
    url: HttpUrl

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str

app = FastAPI(
    title="HoverAI API",
    description="AI-powered web browsing assistant with RAG capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$|^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Lỗi hệ thống: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error", "details": str(exc) if settings.DEBUG else None}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": "Validation Error", "details": exc.errors()}
    )

app.include_router(security.router)

@app.get("/", response_model=BaseResponse)
async def health_check():
    return {"success": True, "data": {"status": "ok"}}

@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    return {
        "status": "healthy",
        "service": "Smart Web AI Assistant API",
        "version": "1.0.0",
        "environment": "development" if settings.DEBUG else "production"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )