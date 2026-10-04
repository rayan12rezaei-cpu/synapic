from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from deep_translator import GoogleTranslator

from app.config import get_settings

settings = get_settings()

LANG_NAMES = {"fa": "Persian", "en": "English", "zh": "Chinese (Simplified)"}
GOOGLE_CODES = {"fa": "fa", "en": "en", "zh": "zh-CN"}


class TranslationError(RuntimeError):
    pass


@dataclass
class TranslationResult:
    text: str
    source: str
    target: str
    provider: str


def _chunks(text: str, limit: int = 3500) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    pieces = re.split(r"(\n\s*\n|(?<=[.!?。！？])\s+)", text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if len(current) + len(piece) > limit and current.strip():
            chunks.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _google(text: str, source: str, target: str) -> str:
    translator = GoogleTranslator(source=GOOGLE_CODES.get(source, source), target=GOOGLE_CODES.get(target, target))
    return "\n\n".join(translator.translate(chunk) for chunk in _chunks(text))


def _libretranslate(text: str, source: str, target: str) -> str:
    payload = {
        "q": text,
        "source": GOOGLE_CODES.get(source, source),
        "target": GOOGLE_CODES.get(target, target),
        "format": "text",
    }
    if settings.libretranslate_api_key:
        payload["api_key"] = settings.libretranslate_api_key
    with httpx.Client(timeout=45) as client:
        response = client.post(settings.libretranslate_url.rstrip("/") + "/translate", json=payload)
        response.raise_for_status()
        data = response.json()
    translated = data.get("translatedText")
    if not translated:
        raise TranslationError("Translation provider returned no translated text.")
    return translated


def _openai_compatible(text: str, source: str, target: str) -> str:
    if not settings.translation_api_key or not settings.translation_model:
        raise TranslationError("OpenAI-compatible translation is not configured.")
    prompt = (
        f"Translate the following text from {LANG_NAMES.get(source, source)} to "
        f"{LANG_NAMES.get(target, target)}. Preserve paragraph breaks. Return only the translation.\n\n{text}"
    )
    url = settings.translation_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.translation_api_key}"}
    payload = {
        "model": settings.translation_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise TranslationError("Translation provider returned an unexpected response.") from exc


def translate_text(text: str, source: str, target: str) -> TranslationResult:
    text = text.strip()
    if not text:
        return TranslationResult("", source, target, settings.translation_provider)
    if source == target:
        return TranslationResult(text, source, target, "identity")
    try:
        provider = settings.translation_provider.lower().strip()
        if provider == "libretranslate":
            translated = _libretranslate(text, source, target)
        elif provider == "openai_compatible":
            translated = _openai_compatible(text, source, target)
        else:
            translated = _google(text, source, target)
        return TranslationResult(translated.strip(), source, target, provider)
    except Exception as exc:
        raise TranslationError(str(exc)) from exc
