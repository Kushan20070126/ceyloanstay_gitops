import json
import os
from typing import Callable

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
NOTIFICATION_QUEUE = "notification_queue"


def consume_notification_events(handler: Callable[[dict], None]) -> None:
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

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    handler(payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as error:
                print(f"Failed to process notification event: {error}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(queue=NOTIFICATION_QUEUE, on_message_callback=on_message)
        print("Listening for notification events...")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection Error: Could not reach RabbitMQ at {RABBITMQ_HOST}.")
    except Exception as error:
        print(f"Notification consumer stopped: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()
