from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytesseract
from PIL import Image, ImageOps

from app.config import get_settings

settings = get_settings()
pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int
    language: str


def _lang_for_ui(language: str) -> str:
    return {"fa": "fas+eng", "en": "eng", "zh": "chi_sim+eng"}.get(language, "eng")


def _preprocess(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    max_side = max(image.size)
    if max_side < 1800:
        scale = min(2.2, 1800 / max_side)
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    arr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    return Image.fromarray(bw)


def _ocr_image(image: Image.Image, language: str) -> tuple[str, float]:
    processed = _preprocess(image)
    tess_lang = _lang_for_ui(language)
    config = "--oem 1 --psm 6"
    data = pytesseract.image_to_data(processed, lang=tess_lang, config=config, output_type=pytesseract.Output.DICT)
    words: list[str] = []
    confidences: list[float] = []
    for txt, raw_conf in zip(data.get("text", []), data.get("conf", [])):
        txt = (txt or "").strip()
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            continue
        if txt and conf >= 0:
            words.append(txt)
            confidences.append(conf)
    text = " ".join(words).strip()
    if not text:
        text = pytesseract.image_to_string(processed, lang=tess_lang, config=config).strip()
    confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
    return text, max(0.0, min(1.0, confidence))


def _pdf_pages(data: bytes) -> list[Image.Image]:
    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[Image.Image] = []
    zoom = settings.ocr_dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pages.append(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
    return pages


def run_ocr(data: bytes, filename: str, language: str) -> OCRResult:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        images = _pdf_pages(data)
    else:
        images = [Image.open(io.BytesIO(data)).convert("RGB")]

    page_texts: list[str] = []
    confs: list[float] = []
    for image in images:
        text, conf = _ocr_image(image, language)
        if text:
            page_texts.append(text)
        confs.append(conf)

    combined = "\n\n".join(page_texts).strip()
    return OCRResult(
        text=combined,
        confidence=sum(confs) / len(confs) if confs else 0.0,
        pages=len(images),
        language=language,
    )
