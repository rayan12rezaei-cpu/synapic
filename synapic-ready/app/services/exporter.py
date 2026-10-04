from __future__ import annotations

import io
import subprocess
from pathlib import Path

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    arabic_reshaper = None
    get_display = None


def _find_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    try:
        out = subprocess.check_output(["fc-match", "sans:style=Regular", "-f", "%{file}"], text=True).strip()
        if out:
            return out
    except Exception:
        pass
    raise FileNotFoundError("No Unicode TTF font is available for PDF export.")


def _pdf_text(text: str) -> str:
    if arabic_reshaper is None or get_display is None:
        return text
    if any("\u0600" <= ch <= "\u06ff" for ch in text):
        return get_display(arabic_reshaper.reshape(text))
    return text


def to_pdf(text: str) -> bytes:
    font_path = _find_font()
    font_name = "SynapicUnicode"
    try:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    except Exception:
        pass

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 42
    font_size = 11
    line_height = 17
    usable_width = width - 2 * margin
    c.setFont(font_name, font_size)

    y = height - margin
    for paragraph in text.splitlines() or [""]:
        shaped = _pdf_text(paragraph)
        words = shaped.split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = (current + " " + word).strip()
            if pdfmetrics.stringWidth(trial, font_name, font_size) <= usable_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            lines = [""]
        for line in lines:
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - margin
            c.drawString(margin, y, line)
            y -= line_height
        y -= 5
    c.save()
    return buffer.getvalue()


def to_docx(text: str) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Noto Sans"
    style.font.size = Pt(11)
    for paragraph in text.split("\n\n"):
        p = doc.add_paragraph(paragraph.strip())
        if any("\u0600" <= ch <= "\u06ff" for ch in paragraph):
            p.paragraph_format.alignment = 2
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def to_markdown(text: str) -> bytes:
    return (text.strip() + "\n").encode("utf-8")


def to_txt(text: str) -> bytes:
    return (text.strip() + "\n").encode("utf-8")
