import json
import os
import time
from typing import Any

import cv2
import numpy as np
import pika
import psycopg2
from minio import Minio
from psycopg2 import pool
from ultralytics import YOLO

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "minioadmin")
DB_DSN = os.getenv("DB_DSN", "dbname=ads user=postgres password=password host=localhost port=5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "ai_processing_queue"
NOTIFICATION_QUEUE = "notification_queue"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "last.pt")

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
MIN_UNIQUE_CLASSES_FOR_VALID_AD = 2

print("Initializing AI Worker Service...")

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

try:
    model = YOLO(MODEL_PATH)
    print(f"AI model loaded: {MODEL_PATH}")
except Exception as error:
    print(f"Failed to load YOLO model: {error}")
    raise SystemExit(1)


def send_notification_event(user_email: str, message: str, ad_id: int | None = None) -> None:
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
        )
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
            result["error"] = "Invalid image data"
            return result

        predictions = model.predict(frame, conf=0.5, verbose=False, device="cpu")

        detected_ids: set[int] = set()
        for prediction in predictions:
            for box in prediction.boxes:
                cls_id = int(box.cls[0])
                if cls_id in LABEL_NAMES:
                    detected_ids.add(cls_id)

        detected_labels = [LABEL_NAMES[i] for i in sorted(detected_ids)]
        result["detected_class_ids"] = sorted(detected_ids)
        result["detected_labels"] = detected_labels
        result["label"] = "normal" if detected_labels else "anomaly"
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
    has_anomaly = any(item["label"] == "anomaly" for item in image_results)

    is_valid_ad = unique_count >= MIN_UNIQUE_CLASSES_FOR_VALID_AD

    summary = {
        "ad_id": ad_id,
        "is_valid_ad": is_valid_ad,
        "unique_label_count": unique_count,
        "unique_labels": unique_labels,
        "has_anomaly_images": has_anomaly,
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
        ad_id = data.get("ad_id")
        images = data.get("images", [])
        user_email = data.get("owner_email")

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
            params = pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
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
