import os
from io import BytesIO
from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "minioadmin")
BUCKET_NAME = "boarding-images"

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False,
)


def ensure_bucket_exists() -> None:
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)


def upload_to_minio(file_data: bytes, file_name: str, content_type: str) -> str:

    ensure_bucket_exists()
    client.put_object(
        BUCKET_NAME,
        file_name,
        BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return file_name


def get_object_stream(file_name: str):

    return client.get_object(BUCKET_NAME, file_name)


def delete_object(file_name: str) -> None:
    client.remove_object(BUCKET_NAME, file_name)
