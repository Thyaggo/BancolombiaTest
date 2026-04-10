FROM python:3.13.13-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright/Crawl4AI
RUN apt-get update 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutar setup de Crawl4AI (instala navegadores de Playwright, etc.)
RUN crawl4ai-setup

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "src/streamlit_app.py", "--server.address", "0.0.0.0"]