from sqlalchemy.orm import Session

from . import models

WELCOME_MESSAGE = "Welcome to CeylonStay. Your account is ready."


def get_notifications(db: Session, email: str):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_email == email)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


def mark_all_as_read(db: Session, email: str):
    (
        db.query(models.Notification)
        .filter(models.Notification.user_email == email, models.Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return {"status": "success"}


def ensure_welcome_notification(db: Session, email: str) -> None:
    exists = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_email == email,
            models.Notification.message == WELCOME_MESSAGE,
        )
        .first()
    )
    if exists:
        return

    row = models.Notification(
        user_email=email,
        message=WELCOME_MESSAGE,
        is_read=False,
    )
    db.add(row)
    db.commit()


def create_notification(
    db: Session,
    *,
    user_email: str,
    message: str,
    ad_id: int | None = None,
    is_read: bool = False,
) -> models.Notification:
    row = models.Notification(
        user_email=user_email,
        ad_id=ad_id,
        message=message,
        is_read=is_read,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
