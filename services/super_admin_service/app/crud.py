from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models


ALLOWED_ADMIN_ROLES = {"admin", "moderator", "ops", "support", "finance"}


def _safe_scalar(db: Session, sql: str, params: dict | None = None) -> int:
    try:
        value = db.execute(text(sql), params or {}).scalar()
        return int(value or 0)
    except Exception:
        return 0


def get_super_admin_kpis(db: Session) -> dict:
    return {
        "total_users": _safe_scalar(db, "SELECT COUNT(*) FROM user_profiles"),
        "total_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads"),
        "active_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'ACTIVE'"),
        "pending_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'PENDING'"),
        "rejected_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'REJECTED'"),
        "total_notifications": _safe_scalar(db, "SELECT COUNT(*) FROM notifications"),
        "unread_notifications": _safe_scalar(db, "SELECT COUNT(*) FROM notifications WHERE is_read = FALSE"),
        "total_admins": _safe_scalar(db, "SELECT COUNT(*) FROM admin_accounts"),
        "active_admins": _safe_scalar(db, "SELECT COUNT(*) FROM admin_accounts WHERE is_active = TRUE"),
    }


def list_admins(db: Session) -> list[models.AdminAccount]:
    return db.query(models.AdminAccount).order_by(models.AdminAccount.id.desc()).all()


def create_admin(db: Session, email: str, role: str, created_by: str) -> models.AdminAccount:
    normalized_role = role.strip().lower()
    if normalized_role not in ALLOWED_ADMIN_ROLES:
        raise ValueError(f"Invalid role: {role}")

    existing = db.query(models.AdminAccount).filter(models.AdminAccount.email == email).first()
    if existing:
        existing.role = normalized_role
        existing.is_active = True
        existing.created_by = created_by
        db.commit()
        db.refresh(existing)
        return existing

    row = models.AdminAccount(
        email=email,
        role=normalized_role,
        is_active=True,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_admin_status(db: Session, admin_id: int, is_active: bool) -> models.AdminAccount | None:
    row = db.query(models.AdminAccount).filter(models.AdminAccount.id == admin_id).first()
    if not row:
        return None
    row.is_active = is_active
    db.commit()
    db.refresh(row)
    return row


def delete_admin(db: Session, admin_id: int) -> bool:
    row = db.query(models.AdminAccount).filter(models.AdminAccount.id == admin_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
