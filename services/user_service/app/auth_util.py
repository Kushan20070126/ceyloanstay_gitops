from fastapi import Header, HTTPException
import base64
import json
from typing import Any


def _decode_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid JWT")

    payload_b64 = parts[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        return json.loads(payload_json)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid JWT payload")


def get_current_user_email(
    authorization: str | None = Header(default=None)
) -> str:

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ")[1]

    payload = _decode_payload(token)

    email = payload.get("email") or payload.get("sub")

    if not email:
        raise HTTPException(status_code=401, detail="Email not found")

    return email