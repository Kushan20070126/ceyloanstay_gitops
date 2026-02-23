from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    id: int
    user_email: str
    message: str
    is_read: bool
    created_at: datetime
    ad_id: Optional[int] = None

    class Config:
        from_attributes = True