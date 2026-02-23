import json
import os
from typing import Any

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )


def get_json(key: str) -> Any | None:
    try:
        value = get_redis_client().get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        return None


def set_json(key: str, value: Any, ttl_seconds: int = 120) -> None:
    try:
        payload = json.dumps(value)
        get_redis_client().setex(key, ttl_seconds, payload)
    except Exception:
       
        return


def delete(key: str) -> None:
    try:
        get_redis_client().delete(key)
    except Exception:
        return


def delete_by_pattern(pattern: str) -> None:
    try:
        client = get_redis_client()
        keys = list(client.scan_iter(match=pattern))
        if keys:
            client.delete(*keys)
    except Exception:
        return
