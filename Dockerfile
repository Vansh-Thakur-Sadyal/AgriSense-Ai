FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    AGRISENSE_STORAGE=/app/storage AGRISENSE_SECURE_COOKIE=1

# libgomp is needed by LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
RUN useradd -u 10001 -m agri && mkdir -p /app/storage /app/config && chown -R agri:agri /app/storage
USER agri
EXPOSE 8150
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8150/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8150", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
