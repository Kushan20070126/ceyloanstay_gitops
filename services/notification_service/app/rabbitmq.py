import json
import os
import time
from typing import Callable

import pika

NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE_NAME", "notification_queue")


def _rabbitmq_retry_delay_seconds() -> int:
    raw_value = os.getenv("RABBITMQ_RETRY_DELAY_SECONDS", "5")
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 5


def _build_rabbitmq_parameters() -> pika.ConnectionParameters | pika.URLParameters:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq.database.svc.cluster.local")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = (
        os.getenv("RABBITMQ_USER")
        or os.getenv("RABBITMQ_USERNAME")
        or os.getenv("RABBITMQ_DEFAULT_USER")
        or "admin"
    )
    password = (
        os.getenv("RABBITMQ_PASS")
        or os.getenv("RABBITMQ_PASSWORD")
        or os.getenv("RABBITMQ_DEFAULT_PASS")
        or "admin123"
    )
    vhost = os.getenv("RABBITMQ_VHOST", "/")

    url = os.getenv("AMQP_URL") or os.getenv("RABBITMQ_URL")
    if url:
        params = pika.URLParameters(url)
        params.heartbeat = 600
        params.blocked_connection_timeout = 300
        return params

    return pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=vhost,
        credentials=pika.PlainCredentials(user, password),
        heartbeat=600,
        blocked_connection_timeout=300,
    )


def consume_notification_events(handler: Callable[[dict], None]) -> None:
    retry_delay = _rabbitmq_retry_delay_seconds()

    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(_build_rabbitmq_parameters())
            channel = connection.channel()
            channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)

            def on_message(ch, method, properties, body):
                try:
                    raw_body = body.decode("utf-8") if isinstance(body, bytes) else str(body)
                    payload = json.loads(raw_body)
                    if not isinstance(payload, dict):
                        raise ValueError("Invalid payload: expected JSON object")

                    handler(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as error:
                    print(f"Failed to process notification event: {error}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=NOTIFICATION_QUEUE, on_message_callback=on_message)
            print("Listening for notification events...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as error:
            print(f"Connection Error: Could not reach RabbitMQ: {error}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        except Exception as error:
            print(f"Notification consumer stopped: {error}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        finally:
            if connection and connection.is_open:
                connection.close()
