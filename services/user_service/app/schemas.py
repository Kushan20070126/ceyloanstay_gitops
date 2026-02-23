from pydantic import BaseModel, EmailStr


class ProfileBase(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None
    description: str | None = None


class ProfileUpdate(ProfileBase):
    pass


class ProfilePatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    description: str | None = None


class ProfileOut(ProfileBase):
    email: EmailStr

    class Config:
        from_attributes = True


class ActionResponse(BaseModel):
    status: str
    message: str
    email: EmailStr
