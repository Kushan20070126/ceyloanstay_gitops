import json
import os
import time
from typing import Any, Callable

import pika

AI_QUEUE_NAME = "ai_processing_queue"
USER_EVENTS_QUEUE_NAME = "user_events_queue"
NOTIFICATION_QUEUE_NAME = "notification_queue"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"Invalid integer for {name}: {raw!r}. Using default {default}.")
        return default


def _retry_delay_seconds() -> int:
    return max(1, _env_int("RABBITMQ_RETRY_DELAY_SECONDS", 5))


def _build_rabbitmq_parameters(
    heartbeat: int = 600,
    blocked_connection_timeout: int = 300,
):
    rabbitmq_url = os.getenv("RABBITMQ_URL") or os.getenv("AMQP_URL")
    if rabbitmq_url:
        params = pika.URLParameters(rabbitmq_url)
        params.heartbeat = heartbeat
        params.blocked_connection_timeout = blocked_connection_timeout
        return params

    host = os.getenv("RABBITMQ_HOST", "rabbitmq.database.svc.cluster.local")
    port = _env_int("RABBITMQ_PORT", 5672)
    vhost = os.getenv("RABBITMQ_VHOST", "/")
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
    credentials = pika.PlainCredentials(user, password)
    return pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=vhost,
        credentials=credentials,
        heartbeat=heartbeat,
        blocked_connection_timeout=blocked_connection_timeout,
    )


def _serialize_message(message: Any) -> tuple[str | bytes, str]:
    if isinstance(message, (dict, list)):
        return json.dumps(message), "application/json"
    if isinstance(message, (bytes, bytearray)):
        return bytes(message), "application/octet-stream"
    if isinstance(message, str):
        return message, "text/plain"
    return str(message), "text/plain"


def _publish(queue_name: str, message: Any) -> None:
    body, content_type = _serialize_message(message)
    connection = None
    try:
        connection = pika.BlockingConnection(_build_rabbitmq_parameters())
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type=content_type,
            ),
        )
    except Exception as error:
        print(f"RabbitMQ publish error for queue {queue_name}: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()


def send_to_ai_queue(ad_id_or_message: Any, images: list[str] | None = None, owner_email: str | None = None) -> None:
    if images is None and owner_email is None:
        payload = ad_id_or_message
    else:
        payload = {
            "ad_id": ad_id_or_message,
            "images": images or [],
            "owner_email": owner_email,
        }
    _publish(AI_QUEUE_NAME, payload)


def send_notification_event(
    user_email: Any = None,
    message: Any = None,
    ad_id: int | None = None,
    **kwargs: Any,
) -> None:
    if isinstance(user_email, dict) and message is None and ad_id is None and not kwargs:
        payload = user_email
    elif isinstance(message, dict) and user_email is None and ad_id is None and not kwargs:
        payload = message
    elif user_email is not None or ad_id is not None or kwargs:
        payload = {
            "user_email": user_email,
            "ad_id": ad_id,
            "message": message,
        }
        payload.update(kwargs)
    else:
        payload = message
    _publish(NOTIFICATION_QUEUE_NAME, payload)


def consume_user_events(handler: Callable[[dict[str, Any]], None]) -> None:
    retry_delay = _retry_delay_seconds()
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(_build_rabbitmq_parameters())
            channel = connection.channel()
            channel.queue_declare(queue=USER_EVENTS_QUEUE_NAME, durable=True)

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
            channel.basic_consume(queue=USER_EVENTS_QUEUE_NAME, on_message_callback=on_message)
            print("Listening for user events...")
            channel.start_consuming()
        except Exception as error:
            print(f"User event consumer error: {error}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        finally:
            if connection and connection.is_open:
                connection.close()
