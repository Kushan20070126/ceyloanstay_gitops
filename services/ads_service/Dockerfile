FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install --upgrade pip && pip install \
    "fastapi[standard]>=0.128.0" \
    "minio>=7.2.20" \
    "pika>=1.3.2" \
    "psycopg2-binary>=2.9.11" \
    "psycopg[binary]>=3.3.2" \
    "python-multipart>=0.0.21" \
    "redis>=6.4.0" \
    "sqlalchemy>=2.0.45" \
    "uvicorn>=0.40.0"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
