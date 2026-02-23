import base64
import json
from typing import Any

from fastapi import Header, HTTPException


def _decode_payload(x_jwt_assertion: str) -> dict[str, Any]:
    parts = x_jwt_assertion.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid X-JWT-Assertion")

    try:
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Payload is not an object")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid X-JWT-Assertion payload")


def get_current_user_email(x_jwt_assertion: str | None = Header(default=None)) -> str:
    if not x_jwt_assertion:
        raise HTTPException(status_code=401, detail="Missing X-JWT-Assertion header")

    payload = _decode_payload(x_jwt_assertion)
    email = payload.get("email") or payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="User email not found in token")

    return str(email)
