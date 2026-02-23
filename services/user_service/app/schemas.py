from pydantic import BaseModel, EmailStr
from typing import Optional

class ProfileBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None

class ProfileUpdate(ProfileBase):
    pass

class ProfileOut(ProfileBase):
    email: EmailStr

    class Config:
        from_attributes = True