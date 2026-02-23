import base64
import json
from typing import Any

from fastapi import Depends, Header, HTTPException


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


def _extract_roles(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("groups") or payload.get("http://wso2.org/claims/role") or []
    if isinstance(raw, str):
        return [role.strip().lower() for role in raw.split(",") if role.strip()]
    if isinstance(raw, list):
        return [str(role).strip().lower() for role in raw if str(role).strip()]
    return []


async def get_current_user_data(x_jwt_assertion: str | None = Header(default=None)) -> dict[str, Any]:
    if not x_jwt_assertion:
        raise HTTPException(status_code=401, detail="Missing X-JWT-Assertion header")

    payload = _decode_payload(x_jwt_assertion)
    email = payload.get("email") or payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="User email not found in token")

    return {"email": str(email), "roles": _extract_roles(payload), "raw": payload}


async def require_admin_or_super_admin(
    user_data: dict[str, Any] = Depends(get_current_user_data),
) -> dict[str, Any]:
    roles = user_data.get("roles", [])
    if "admin" not in roles and "super_admin" not in roles and "superadmin" not in roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_data
