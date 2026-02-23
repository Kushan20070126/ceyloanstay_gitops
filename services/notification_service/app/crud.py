from sqlalchemy.orm import Session
from . import models

def get_notifications(db: Session, email: str):
    return db.query(models.Notification).filter(
        models.Notification.user_email == email
    ).order_by(models.Notification.created_at.desc()).all()

def mark_all_as_read(db: Session, email: str):
    db.query(models.Notification).filter(
        models.Notification.user_email == email,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success"}