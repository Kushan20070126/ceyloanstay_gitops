from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from . import auth_util, crud, database, models, rabbitmq, schemas
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay User Service")


@app.get("/profile", response_model=schemas.ProfileOut)
def read_profile(
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(database.get_db),
):
    profile = crud.get_profile(db, email)
    if not profile:
        return {
            "email": email,
            "name": "",
            "phone": "",
            "address": "",
            "description": "",
        }
    return profile


@app.put("/profile", response_model=schemas.ProfileOut)
def update_profile(
    profile_data: schemas.ProfileUpdate,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(database.get_db),
):
    return crud.sync_profile(db, profile_data, email)


@app.patch("/profile", response_model=schemas.ProfileOut)
def patch_profile(
    profile_data: schemas.ProfilePatch,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(database.get_db),
):
    return crud.patch_profile(db, profile_data, email)


@app.post("/account/deactivate", response_model=schemas.ActionResponse)
def deactivate_account(email: str = Depends(auth_util.get_current_user_email)):
    rabbitmq.publish_user_event("user_deactivated", email)
    return {
        "status": "success",
        "message": "User deactivated event published",
        "email": email,
    }


@app.delete("/account", response_model=schemas.ActionResponse)
def delete_account(
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(database.get_db),
):
    crud.delete_profile(db, email)
    rabbitmq.publish_user_event("user_deleted", email)
    return {
        "status": "success",
        "message": "User deleted and event published",
        "email": email,
    }
