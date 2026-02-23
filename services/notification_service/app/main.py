import threading

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import auth_util, crud, models, rabbitmq, schemas
from .database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_notification_event(payload: dict) -> None:
    user_email = payload.get("user_email")
    message = payload.get("message")
    ad_id = payload.get("ad_id")

    if not user_email or not message:
        return

    db = SessionLocal()
    try:
        crud.create_notification(
            db,
            user_email=str(user_email),
            message=str(message),
            ad_id=int(ad_id) if ad_id is not None else None,
        )
    finally:
        db.close()


@app.on_event("startup")
def start_notification_consumer() -> None:
    worker = threading.Thread(
        target=rabbitmq.consume_notification_events,
        args=(process_notification_event,),
        daemon=True,
    )
    worker.start()


@app.get("/notifications", response_model=list[schemas.NotificationBase])
def get_user_notifications(
    db: Session = Depends(get_db),
    email: str = Depends(auth_util.get_current_user_email),
):
    crud.ensure_welcome_notification(db, email)
    return crud.get_notifications(db, email)


@app.put("/notifications/mark-read")
def mark_read(
    db: Session = Depends(get_db),
    email: str = Depends(auth_util.get_current_user_email),
):
    return crud.mark_all_as_read(db, email)
