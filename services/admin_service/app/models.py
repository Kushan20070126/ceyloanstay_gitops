from sqlalchemy import Column, Float, Integer, String

from .database import Base


class PropertyAd(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    owner_email = Column(String)
    title = Column(String)
    price = Column(Float)
    district = Column(String)
    status = Column(String)
