import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db

DEFAULT_SUPER_ADMIN_EMAILS = "kushanherath59@gmail.com"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _get_super_admin_emails() -> set[str]:
    configured = os.getenv("SUPER_ADMIN_EMAILS") or os.getenv("SUPER_ADMIN_EMAIL") or DEFAULT_SUPER_ADMIN_EMAILS
    return {_normalize_email(item) for item in configured.split(",") if item.strip()}


def _is_super_admin_in_db(db: Session, email: str) -> bool:
    try:
        row = db.execute(
            text(
                """
                SELECT role, is_active
                FROM admin_accounts
                WHERE lower(email) = :email
                LIMIT 1
                """
            ),
            {"email": email},
        ).mappings().first()
    except Exception:
        return False

    if not row:
        return False
    role = str(row.get("role") or "").strip().lower()
    return bool(row.get("is_active")) and role == "super_admin"


def get_current_user_email(
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
) -> str:
    email = _normalize_email(x_user_email or "")
    if not email:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header")
    return email


def require_super_admin(
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    if email in _get_super_admin_emails() or _is_super_admin_in_db(db, email):
        return {"email": email, "role": "super_admin"}
    raise HTTPException(status_code=403, detail="Super admin access required")
