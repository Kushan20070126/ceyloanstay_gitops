from sqlalchemy import Column, Integer, String, Text
from .database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False) # Linked to Google Email
    name = Column(String)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    description = Column(Text, nullable=True)