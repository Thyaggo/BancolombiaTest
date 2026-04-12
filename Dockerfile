FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright/Crawl4AI
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium / Playwright
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxkbcommon0 \
    libgtk-3-0 \
    # Compilación de extensiones C (cffi, cryptography, etc.)
    gcc \
    libffi-dev \
    libssl-dev \
    # Utilidades básicas
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutar setup de Crawl4AI (instala navegadores de Playwright, etc.)
RUN crawl4ai-setup

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "src/streamlit_app.py", "--server.address", "0.0.0.0"]