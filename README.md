# Synapic

Synapic is a FastAPI web application for extracting text from handwritten notes/images, translating the extracted text, reading either version aloud in the browser, and exporting the active text as PDF, DOCX, Markdown, or TXT.

## Stack

- FastAPI + Jinja2
- Tesseract OCR (English, Persian, Simplified Chinese; packaged in Docker)
- PyMuPDF for optional PDF input
- Browser Web Speech API for text-to-speech
- Configurable translation provider: Google web translator by default, or LibreTranslate / OpenAI-compatible endpoint via environment variables
- Responsive glassmorphism frontend with Persian, English, and Simplified Chinese UI

## Local run

1. Install Tesseract if you are not using Docker. The application expects `tesseract` on PATH.
2. Create a virtual environment and install Python packages:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust values as needed.
4. Start:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Docker

```bash
docker build -t synapic .
docker run --rm -p 8000:8000 --env-file .env synapic
```

## Render

This repository includes `render.yaml` and a production-oriented `Dockerfile`. Render supports Docker-backed web services and uses the Dockerfile `CMD` unless a dashboard start command overrides it. The included Blueprint declares an HTTP health check at `/healthz`. See the official Render documentation for the exact dashboard flow: https://render.com/docs/docker and https://render.com/docs/blueprint-spec

### Deploy with the Blueprint

1. Put this folder in a GitHub repository.
2. In Render, create a new Blueprint and select the repository.
3. Render reads `render.yaml`, builds the Docker image, and starts the web service.
4. In Render environment settings, set any optional translation variables you need.
5. Open the generated `onrender.com` URL.

For a production deployment with persistent uploads/exports, attach a persistent disk and set `SYNAPIC_STORAGE_DIR=/var/data` plus `disk` settings in the Render service. The current app cleans temporary files automatically, so a persistent disk is not required for normal request/response use.

## Translation providers

Default:

```env
TRANSLATION_PROVIDER=google
```

Optional LibreTranslate:

```env
TRANSLATION_PROVIDER=libretranslate
LIBRETRANSLATE_URL=https://libretranslate.com
LIBRETRANSLATE_API_KEY=
```

Optional OpenAI-compatible provider:

```env
TRANSLATION_PROVIDER=openai_compatible
TRANSLATION_API_KEY=...
TRANSLATION_BASE_URL=https://api.openai.com/v1
TRANSLATION_MODEL=your-model
```

Keep secrets server-side; never put API keys in the frontend code.

## Notes on handwriting

Tesseract is used with image preprocessing and language selection. Handwritten text is inherently more difficult for OCR than printed text, so output quality depends heavily on image clarity, lighting, handwriting style, and language. The application exposes OCR confidence so the frontend can show whether the result is high, medium, or low confidence.
