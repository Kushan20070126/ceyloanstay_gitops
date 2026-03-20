from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models

_facilities_table_ready = False


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


def _ensure_facilities_table(db: Session) -> None:
    global _facilities_table_ready
    if _facilities_table_ready:
        return

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS facilities (
                id SERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL
            )
            """
        )
    )
    db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_facilities_name_lower ON facilities (LOWER(name))"))
    db.commit()
    _facilities_table_ready = True


def list_facilities(db: Session, query: str | None = None, limit: int = 100, skip: int = 0) -> list[dict]:
    _ensure_facilities_table(db)
    normalized_query = query.strip() if query else None
    pattern = f"%{normalized_query}%" if normalized_query else None
    return _safe_rows(
        db,
        """
        SELECT id, name
        FROM facilities
        WHERE (:pattern IS NULL OR name ILIKE :pattern)
        ORDER BY name ASC, id ASC
        OFFSET :skip
        LIMIT :limit
        """,
        {"pattern": pattern, "skip": skip, "limit": limit},
    )


def create_facility(db: Session, name: str) -> tuple[dict, bool]:
    _ensure_facilities_table(db)

    normalized_name = " ".join(name.split())
    if not normalized_name:
        raise ValueError("Facility name cannot be empty.")

    inserted = (
        db.execute(
            text(
                """
                INSERT INTO facilities (name)
                VALUES (:name)
                ON CONFLICT DO NOTHING
                RETURNING id, name
                """
            ),
            {"name": normalized_name},
        )
        .mappings()
        .first()
    )
    if inserted:
        db.commit()
        return dict(inserted), True

    existing = (
        db.execute(
            text(
                """
                SELECT id, name
                FROM facilities
                WHERE LOWER(name) = LOWER(:name)
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"name": normalized_name},
        )
        .mappings()
        .first()
    )
    if existing:
        return dict(existing), False

    raise RuntimeError("Failed to create or fetch facility.")
