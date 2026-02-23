from sqlalchemy.orm import Session
from . import models, schemas

def get_profile(db: Session, email: str):
    return db.query(models.UserProfile).filter(models.UserProfile.email == email).first()

def sync_profile(db: Session, profile_data: schemas.ProfileUpdate, email: str):
    db_profile = get_profile(db, email)
    
    if db_profile:
   
        for key, value in profile_data.model_dump().items():
            setattr(db_profile, key, value)
    else:
       
        db_profile = models.UserProfile(
            **profile_data.model_dump(),
            email=email
        )
        db.add(db_profile)
    
    db.commit()
    db.refresh(db_profile)
    return db_profile