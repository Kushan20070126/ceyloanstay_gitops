import base64
import json
from typing import Any

from fastapi import Depends, Header, HTTPException


def _decode_payload(x_jwt_assertion: str) -> dict[str, Any]:
    # JWT format: header.payload.signature
    parts = x_jwt_assertion.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid X-JWT-Assertion")

    try:
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)  # base64 padding
        payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Payload is not an object")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid X-JWT-Assertion payload")


async def get_current_user_data(x_jwt_assertion: str | None = Header(default=None)) -> dict[str, Any]:
    """
    Read user info from WSO2/Bijira `X-JWT-Assertion`.
    Gateway does signature validation; this service only decodes payload.
    """
    if not x_jwt_assertion:
        raise HTTPException(status_code=401, detail="Missing X-JWT-Assertion header")

    payload = _decode_payload(x_jwt_assertion)
    email = payload.get("email") or payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="User email not found in token")

    roles = payload.get("groups") or payload.get("http://wso2.org/claims/role") or []
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",") if r.strip()]
    elif not isinstance(roles, list):
        roles = []

    return {
        "email": str(email),
        "roles": roles,
        "raw": payload,
    }


async def get_current_user_email(
    user_data: dict[str, Any] = Depends(get_current_user_data),
) -> str:
    return str(user_data["email"])
