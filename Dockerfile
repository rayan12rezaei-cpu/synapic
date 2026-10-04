FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       tesseract-ocr-eng \
       tesseract-ocr-fas \
       tesseract-ocr-chi-sim \
       fonts-dejavu \
       fonts-noto-cjk \
       fontconfig \
       libgl1 \
       libglib2.0-0 \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /opt/venv
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY assets ./assets
COPY storage ./storage
COPY .env.example ./
COPY README.md ./
COPY render.yaml ./

RUN useradd --create-home --shell /usr/sbin/nologin synapic \
    && chown -R synapic:synapic /app
USER synapic

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
