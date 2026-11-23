# --- 1. lépés: függőségek telepítése külön rétegbe ---
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 2. lépés: futtatható image ---
FROM base AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    DB_PATH=/data/fitbook.db
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
COPY app ./app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
