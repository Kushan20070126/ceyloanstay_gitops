import json
import os
from typing import Callable

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "ai_processing_queue"
USER_EVENTS_QUEUE = "user_events_queue"
NOTIFICATION_QUEUE = "notification_queue"


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
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection Error: Could not reach RabbitMQ at {RABBITMQ_HOST}.")
    except Exception as error:
        print(f"Failed to publish notification event: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()


def consume_user_events(handler: Callable[[dict], None]) -> None:
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
        channel.queue_declare(queue=USER_EVENTS_QUEUE, durable=True)

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    handler(payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as error:
                print(f"Failed to process user event: {error}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(queue=USER_EVENTS_QUEUE, on_message_callback=on_message)
        print("Listening for user events...")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection Error: Could not reach RabbitMQ at {RABBITMQ_HOST}.")
    except Exception as error:
        print(f"User event consumer stopped: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()
