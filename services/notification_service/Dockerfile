FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --upgrade pip && pip install \
    "fastapi[standard]>=0.128.0" \
    "pika>=1.3.2" \
    "psycopg2-binary>=2.9.11" \
    "python-jose>=3.5.0" \
    "sqlalchemy>=2.0.45" \
    "uvicorn>=0.40.0"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
