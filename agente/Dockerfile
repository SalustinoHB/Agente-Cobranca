# ============================================================
# Agente Cobrança Renaissance — Dockerfile
# Python 3.11 + Playwright (Chromium) headless + FastAPI
# ============================================================

FROM python:3.11-slim

# Sistema: deps Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg curl ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    fonts-liberation \
    tesseract-ocr tesseract-ocr-por poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium pro Playwright
RUN playwright install chromium && playwright install-deps chromium

# Código
COPY . /app/agente/
RUN touch /app/agente/__init__.py

# Pasta de dados (volume)
RUN mkdir -p /data
VOLUME /data

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Fortaleza

# Expõe porta da API
EXPOSE 5000

# Default: roda API + scheduler em paralelo
# (em produção, ideal é separar containers; aqui é simples)
CMD ["sh", "-c", "uvicorn agente.api:app --host 0.0.0.0 --port 5000 & python -m agente.main"]
