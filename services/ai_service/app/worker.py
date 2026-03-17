import json
import os
import time
from typing import Any

import cv2
import numpy as np
import pika
import psycopg2
from minio import Minio
from ultralytics import YOLO


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"Invalid integer for {name}: {raw!r}. Using default {default}.")
        return default


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "minioadmin")
DB_DSN = os.getenv("DB_DSN", "dbname=ads user=postgres password=password host=localhost port=5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = _env_int("RABBITMQ_PORT", 5672)
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = (
    os.getenv("RABBITMQ_USER")
    or os.getenv("RABBITMQ_USERNAME")
    or os.getenv("RABBITMQ_DEFAULT_USER")
    or "guest"
)
RABBITMQ_PASS = (
    os.getenv("RABBITMQ_PASS")
    or os.getenv("RABBITMQ_PASSWORD")
    or os.getenv("RABBITMQ_DEFAULT_PASS")
    or "guest"
)
RABBITMQ_URL = os.getenv("RABBITMQ_URL") or os.getenv("AMQP_URL")
QUEUE_NAME = "ai_processing_queue"
NOTIFICATION_QUEUE = "notification_queue"
YOLO_CONFIG_DIR = os.getenv("YOLO_CONFIG_DIR", "/tmp/Ultralytics")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.getenv("AI_MODEL_PATH", os.path.join(BASE_DIR, "last.pt"))
CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.5"))
MIN_UNIQUE_CLASSES_FOR_VALID_AD = int(os.getenv("MIN_UNIQUE_CLASSES_FOR_VALID_AD", "2"))

LABEL_NAMES = {
    0: "bed",
    1: "table",
    2: "chair",
    3: "fan",
    4: "door",
    5: "mattress",
    6: "pillow",
    7: "cupboard",
    8: "light",
    9: "window",
    10: "mosquitonet",
    11: "comed",
    12: "shower",
    13: "sink",
    14: "mirror",
}


def _ensure_yolo_dirs() -> None:
    # Ultralytics writes config/cache files; keep path writable in containers.
    for path in {YOLO_CONFIG_DIR, os.path.join(YOLO_CONFIG_DIR, "Ultralytics"), "/tmp/Ultralytics"}:
        try:
            os.makedirs(path, exist_ok=True)
            os.chmod(path, 0o777)
        except Exception as error:
            print(f"Warning: failed to prepare YOLO path '{path}': {error}")


def _build_rabbitmq_parameters(
    heartbeat: int = 600,
    blocked_connection_timeout: int = 300,
):
    if RABBITMQ_URL:
        params = pika.URLParameters(RABBITMQ_URL)
        params.heartbeat = heartbeat
        params.blocked_connection_timeout = blocked_connection_timeout
        return params

    return pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
        heartbeat=heartbeat,
        blocked_connection_timeout=blocked_connection_timeout,
    )


_ensure_yolo_dirs()

print(f"Initializing AI Worker Service (YOLO mode) with model: {MODEL_PATH}")
print(
    "RabbitMQ config:",
    json.dumps(
        {
            "host": RABBITMQ_HOST,
            "port": RABBITMQ_PORT,
            "vhost": RABBITMQ_VHOST,
            "user": RABBITMQ_USER,
            "url_mode": bool(RABBITMQ_URL),
        },
        ensure_ascii=True,
    ),
)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False,
)

try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DB_DSN)
    print("Database connection pool ready.")
except Exception as error:
    print(f"Failed to initialize DB: {error}")
    raise SystemExit(1)

if not os.path.exists(MODEL_PATH):
    print(f"Model file not found: {MODEL_PATH}")
    raise SystemExit(1)

try:
    model = YOLO(MODEL_PATH)
    print("YOLO model loaded successfully.")
except Exception as error:
    print(f"Failed to load YOLO model: {error}")
    raise SystemExit(1)


def send_notification_event(user_email: str, message: str, ad_id: int | None = None) -> None:
    connection = None
    try:
        connection = pika.BlockingConnection(_build_rabbitmq_parameters())
        channel = connection.channel()
        channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)

        payload = json.dumps({
            "user_email": user_email,
            "ad_id": ad_id,
            "message": message,
        })
        channel.basic_publish(
            exchange="",
            routing_key=NOTIFICATION_QUEUE,
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
    except Exception as error:
        print(f"Failed to publish notification event: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()


def _decode_image(image_bytes: bytes):
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)


def classify_single_image(image_name: str) -> dict[str, Any]:
    response = None
    clean_name = image_name.split("/")[-1] if "/" in image_name else image_name

    result: dict[str, Any] = {
        "image": clean_name,
        "label": "anomaly",
        "detected_labels": [],
        "detected_class_ids": [],
        "error": None,
    }

    try:
        response = minio_client.get_object("boarding-images", clean_name)
        frame = _decode_image(response.read())
        if frame is None:
            result["error"] = "invalid_image"
            return result

        predictions = model.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False, device="cpu")
        detected_ids: set[int] = set()

        for prediction in predictions:
            for box in prediction.boxes:
                cls_id = int(box.cls[0])
                if cls_id in LABEL_NAMES:
                    detected_ids.add(cls_id)

        labels = [LABEL_NAMES[i] for i in sorted(detected_ids)]
        result["detected_class_ids"] = sorted(detected_ids)
        result["detected_labels"] = labels
        result["label"] = "normal" if labels else "anomaly"
        return result

    except Exception as error:
        result["error"] = str(error)
        return result
    finally:
        if response:
            response.close()
            response.release_conn()


def classify_ad_images(ad_id: int, image_paths: list[str]) -> dict[str, Any]:
    image_results: list[dict[str, Any]] = []
    all_detected_ids: set[int] = set()

    for path in image_paths:
        image_result = classify_single_image(path)
        image_results.append(image_result)
        all_detected_ids.update(image_result.get("detected_class_ids", []))

    unique_count = len(all_detected_ids)
    unique_labels = [LABEL_NAMES[i] for i in sorted(all_detected_ids)]
    anomaly_count = sum(1 for item in image_results if item.get("label") == "anomaly")
    is_valid_ad = unique_count >= MIN_UNIQUE_CLASSES_FOR_VALID_AD

    summary = {
        "ad_id": ad_id,
        "is_valid_ad": is_valid_ad,
        "unique_label_count": unique_count,
        "unique_labels": unique_labels,
        "total_images": len(image_results),
        "anomaly_images": anomaly_count,
        "images": image_results,
    }

    print(f"Ad {ad_id} classification summary: {json.dumps(summary, ensure_ascii=True)}")
    return summary


def update_ad_and_notify(ad_id: int, status: str, user_email: str | None, summary: dict[str, Any]) -> None:
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("UPDATE ads SET status = %s WHERE id = %s", (status, ad_id))
            conn.commit()
            print(f"Ad {ad_id} updated to {status}.")

        if user_email:
            if status == "ACTIVE":
                labels = ", ".join(summary.get("unique_labels", [])) or "none"
                message = f"Your ad is approved and now active. Detected labels: {labels}."
            else:
                labels = ", ".join(summary.get("unique_labels", [])) or "none"
                anomaly_images = [
                    item.get("image")
                    for item in summary.get("images", [])
                    if item.get("label") == "anomaly"
                ]
                flagged = ", ".join(anomaly_images) if anomaly_images else "unknown"
                message = (
                    "Your ad was rejected. Images were flagged as anomaly or insufficient features. "
                    f"Flagged images: {flagged}. Detected labels: {labels}."
                )

            send_notification_event(user_email=user_email, ad_id=ad_id, message=message)

    except Exception as error:
        print(f"DB Error during update: {error}")
    finally:
        if conn:
            db_pool.putconn(conn)


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("Invalid task payload: expected JSON object")

        ad_id_raw = data.get("ad_id")
        if ad_id_raw is None:
            raise ValueError("Missing ad_id in task payload")
        ad_id = int(ad_id_raw)

        images = data.get("images")
        if images is None:
            images = data.get("uploaded_filenames", [])
        if not isinstance(images, list):
            images = [images]
        images = [str(item) for item in images if str(item).strip()]

        user_email = data.get("owner_email") or data.get("email") or data.get("user_email")

        print(f"Task received: ad={ad_id}, owner={user_email}, images={len(images)}")

        summary = classify_ad_images(ad_id, images)
        new_status = "ACTIVE" if summary["is_valid_ad"] else "REJECTED"
        update_ad_and_notify(ad_id, new_status, user_email, summary)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Ad {ad_id} processing finished.\n")
    except Exception as error:
        print(f"Worker error: {error}")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def run_worker():
    while True:
        try:
            params = _build_rabbitmq_parameters()
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("AI Worker waiting for messages...")
            channel.start_consuming()
        except Exception as error:
            print(f"Connection lost: {error}. Retrying in 5s...")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
