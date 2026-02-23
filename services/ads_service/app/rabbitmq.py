import json
import os

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "ai_processing_queue"


def send_to_ai_queue(ad_id: int, images: list[str], owner_email: str) -> None:
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
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        message = json.dumps({
            "ad_id": ad_id,
            "images": images,
            "owner_email": owner_email,
        })

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        print(f" [x] Sent Task for Ad {ad_id} (User: {owner_email}) to AI Queue")

    except pika.exceptions.AMQPConnectionError:
        print(f"Connection Error: Could not reach RabbitMQ at {RABBITMQ_HOST}.")
    except Exception as error:
        print(f"Failed to push to RabbitMQ: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()
