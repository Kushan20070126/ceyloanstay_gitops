from datetime import datetime

from pydantic import BaseModel, EmailStr


class SuperAdminKPIOut(BaseModel):
    total_users: int
    total_ads: int
    active_ads: int
    pending_ads: int
    rejected_ads: int
    total_notifications: int
    unread_notifications: int
    total_admins: int
    active_admins: int


class AdminAccountCreate(BaseModel):
    email: EmailStr
    role: str = "admin"


class AdminAccountOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True
