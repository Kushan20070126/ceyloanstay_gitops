import pika
import json
import cv2
import numpy as np
import psycopg2
from psycopg2 import pool
import os
import time
from minio import Minio
from ultralytics import YOLO

# Environment Configurations
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "minioadmin")
DB_DSN = os.getenv("DB_DSN", "dbname=ads user=postgres password=password host=localhost port=5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "last.pt")

print(f"🚀 Initializing AI Worker Service...")

LABEL_NAMES = {
    0: 'bed', 1: 'table', 2: 'chair', 3: 'fan', 4: 'door',
    5: 'mattress', 6: 'pillow', 7: 'cupboard', 8: 'light',
    9: 'window', 10: 'mosquitonet', 11: 'comed', 12: 'shower',
    13: 'sink', 14: 'mirror'
}

# Clients Initialization
minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DB_DSN)
    # --- SCHEMA FIX: Ensure notifications table exists ---
    conn = db_pool.getconn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255),
                ad_id INTEGER,
                message TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    db_pool.putconn(conn)
    print("✅ Database connection pool created and schema verified.")
except Exception as e:
    print(f"❌ Failed to initialize DB: {e}")
    exit(1)

try:
    model = YOLO(MODEL_PATH)
    print(f"✅ AI Model loaded: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {e}")
    exit(1)

def process_images(ad_id, image_paths):
    detected_unique_classes = set()
    
    for path in image_paths:
        response = None
        try:
            clean_path = path.split('/')[-1] if '/' in path else path
            response = minio_client.get_object("boarding-images", clean_path)
            
            file_bytes = np.asarray(bytearray(response.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # FIX: Forced device='cpu' to avoid CUDA NoKernelImage error
            results = model.predict(frame, conf=0.5, verbose=False, device='cpu')
            
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id in LABEL_NAMES:
                        detected_unique_classes.add(cls_id)
        
        except Exception as e:
            print(f"❌ Error processing image {path}: {e}")
        finally:
            if response:
                response.close()
                response.release_conn()

    unique_count = len(detected_unique_classes)
    found_labels = [LABEL_NAMES[i] for i in detected_unique_classes]
    print(f"📊 Ad {ad_id}: Found {unique_count} unique classes: {found_labels}")
    
    return unique_count >= 2

def update_ad_and_notify(ad_id, status, user_email):
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Update Ad Status
            cur.execute("UPDATE ads SET status = %s WHERE id = %s", (status, ad_id))
            
            # Only notify if we have a valid email and it was rejected
            if status == "REJECTED" and user_email:
                msg = "❌ Your ad was rejected. AI could not verify at least 2 boarding facilities in your images."
                cur.execute(
                    "INSERT INTO notifications (user_email, ad_id, message, is_read, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    (user_email, ad_id, msg, False)
                )
            conn.commit()
            print(f"🔄 Ad {ad_id} updated to {status}.")
    except Exception as e:
        print(f"❌ DB Error during update: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        ad_id = data.get('ad_id')
        images = data.get('images', [])
        user_email = data.get('owner_email') 

        print(f"📥 Task Received: Ad {ad_id} for {user_email}")

        is_valid = process_images(ad_id, images)
        new_status = "ACTIVE" if is_valid else "REJECTED"
        
        update_ad_and_notify(ad_id, new_status, user_email)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"✅ Ad {ad_id} processing finished.\n")

    except Exception as e:
        print(f"🔥 Worker Error: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

def run_worker():
    while True:
        try:
            params = pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue='ai_processing_queue', durable=True)
            channel.basic_qos(prefetch_count=1) 
            channel.basic_consume(queue='ai_processing_queue', on_message_callback=callback)
            print("😴 AI Worker standby. Waiting for images...")
            channel.start_consuming()
        except Exception as e:
            print(f"⚠️ Connection lost: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    run_worker()