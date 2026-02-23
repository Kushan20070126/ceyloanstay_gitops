from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import database, models, schemas, crud, auth_util
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/profile", response_model=schemas.ProfileOut)
def read_profile(
    email: str = Depends(auth_util.get_current_user_email), 
    db: Session = Depends(database.get_db)
):
    profile = crud.get_profile(db, email)
    if not profile:
        #
        return {"email": email, "name": "", "phone": "", "address": "", "description": ""}
    return profile

@app.put("/profile", response_model=schemas.ProfileOut)
def update_profile(
    profile_data: schemas.ProfileUpdate,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(database.get_db)
):
    return crud.sync_profile(db, profile_data, email)