from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models


def _safe_scalar(db: Session, sql: str, params: dict | None = None) -> int:
    try:
        value = db.execute(text(sql), params or {}).scalar()
        return int(value or 0)
    except Exception:
        return 0


def _safe_rows(db: Session, sql: str, params: dict | None = None) -> list[dict]:
    try:
        rows = db.execute(text(sql), params or {}).mappings().all()
        return [dict(row) for row in rows]
    except Exception:
        return []


def get_admin_kpis(db: Session) -> dict:
    return {
        "total_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads"),
        "active_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'ACTIVE'"),
        "pending_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'PENDING'"),
        "rejected_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'REJECTED'"),
        "draft_ads": _safe_scalar(db, "SELECT COUNT(*) FROM ads WHERE status = 'DRAFT'"),
        "total_clicks": _safe_scalar(db, "SELECT COUNT(*) FROM ad_clicks"),
        "total_notifications": _safe_scalar(db, "SELECT COUNT(*) FROM notifications"),
        "unread_notifications": _safe_scalar(db, "SELECT COUNT(*) FROM notifications WHERE is_read = FALSE"),
    }


def get_recent_ads(db: Session, limit: int = 10) -> list[dict]:
    return _safe_rows(
        db,
        """
        SELECT id, owner_email, title, price, district, status
        FROM ads
        ORDER BY id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


def list_ads(db: Session, status: str | None = None, limit: int = 100, skip: int = 0) -> list[models.PropertyAd]:
    query = db.query(models.PropertyAd)
    if status:
        query = query.filter(models.PropertyAd.status == status)
    return query.order_by(models.PropertyAd.id.desc()).offset(skip).limit(limit).all()
