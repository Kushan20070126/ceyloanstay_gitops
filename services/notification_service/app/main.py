from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, crud, auth_util
from .database import engine, Base, get_db


Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/notifications", response_model=list[schemas.NotificationBase])
def get_user_notifications(
    db: Session = Depends(get_db),
    email: str = Depends(auth_util.get_current_user_email)
):
    return crud.get_notifications(db, email)

@app.put("/notifications/mark-read")
def mark_read(
    db: Session = Depends(get_db),
    email: str = Depends(auth_util.get_current_user_email)
):
    return crud.mark_all_as_read(db, email)