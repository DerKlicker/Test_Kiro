# syntax=docker/dockerfile:1

# ---- Basis-Image ----
# Schlankes, offizielles Python-Image.
FROM python:3.11-slim

# Python-Umgebung: keine .pyc-Dateien, Logs sofort ausgeben.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000

WORKDIR /app

# Abhängigkeiten zuerst (bessere Docker-Layer-Cache-Nutzung).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode kopieren.
COPY app.py notion_helper.py bring_helper.py ssl_helper.py ./
COPY templates ./templates

# Aus Sicherheitsgründen als nicht-root Benutzer laufen.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Produktions-Webserver: Gunicorn.
# - 2 Worker, je 4 Threads: reicht locker für ein kleines internes Tool
#   und erlaubt mehrere parallele Übertragungen.
# - timeout 120s, da Notion/Bring!-Aufrufe etwas dauern können.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
