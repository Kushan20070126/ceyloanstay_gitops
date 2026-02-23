import json
import os

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
USER_EVENTS_QUEUE = "user_events_queue"


def publish_user_event(event: str, email: str) -> None:
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

        message = json.dumps({"event": event, "email": email})
        channel.basic_publish(
            exchange="",
            routing_key=USER_EVENTS_QUEUE,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
    except pika.exceptions.AMQPConnectionError:
        print(f"Connection Error: Could not reach RabbitMQ at {RABBITMQ_HOST}.")
    except Exception as error:
        print(f"Failed to publish user event: {error}")
    finally:
        if connection and connection.is_open:
            connection.close()
