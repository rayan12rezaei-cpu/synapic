from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.exporter import to_docx, to_markdown, to_pdf, to_txt
from app.services.ocr import run_ocr
from app.services.translator import TranslationError, translate_text

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title=settings.app_name, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}
ALLOWED_LANGS = {"fa", "en", "zh"}


class TranslateRequest(BaseModel):
    text: str = Field(min_length=0, max_length=200_000)
    source: str
    target: str


@app.get("/", response_class=FileResponse)
async def index():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/ocr")
async def ocr(file: Annotated[UploadFile, File(...)], language: str = "fa"):
    language = language.lower().strip()
    if language not in ALLOWED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported OCR language.")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Maximum upload size is {settings.max_upload_mb} MB.")

    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if suffix != ".pdf" and not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="The selected file is not a supported image.")

    try:
        result = run_ocr(data, file.filename or "upload", language)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

    return JSONResponse(
        {
            "text": result.text,
            "confidence": round(result.confidence, 4),
            "pages": result.pages,
            "language": result.language,
            "filename": file.filename,
        }
    )


@app.post("/api/translate")
async def translate(payload: TranslateRequest):
    source = payload.source.lower().strip()
    target = payload.target.lower().strip()
    if source not in ALLOWED_LANGS or target not in ALLOWED_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported translation language.")
    try:
        result = translate_text(payload.text, source, target)
    except TranslationError as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc
    return {"text": result.text, "source": result.source, "target": result.target, "provider": result.provider}


class ExportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300_000)
    format: str


@app.post("/api/export")
async def export(payload: ExportRequest):
    fmt = payload.format.lower().strip()
    if fmt == "pdf":
        body = to_pdf(payload.text)
        media = "application/pdf"
        filename = "synapic-export.pdf"
    elif fmt == "docx":
        body = to_docx(payload.text)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "synapic-export.docx"
    elif fmt == "md":
        body = to_markdown(payload.text)
        media = "text/markdown; charset=utf-8"
        filename = "synapic-export.md"
    elif fmt == "txt":
        body = to_txt(payload.text)
        media = "text/plain; charset=utf-8"
        filename = "synapic-export.txt"
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format.")

    return StreamingResponse(
        iter([body]),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
