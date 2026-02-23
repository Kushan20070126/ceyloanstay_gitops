FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Force CPU-only torch wheels so image stays smaller and avoids CUDA deps.
RUN pip install --upgrade pip && \
    pip install --index-url https://download.pytorch.org/whl/cpu \
      torch torchvision && \
    pip install \
      "fastapi[standard]>=0.128.0" \
      "minio>=7.2.20" \
      "numpy>=2.4.1" \
      "opencv-python-headless>=4.12.0.88" \
      "pika>=1.3.2" \
      "psycopg2-binary>=2.9.11" \
      "ultralytics>=8.3.0" \
      "uvicorn>=0.40.0"

COPY app ./app

CMD ["python", "app/worker.py"]
