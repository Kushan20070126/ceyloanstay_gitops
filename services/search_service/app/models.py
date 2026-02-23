from sqlalchemy import Column, Float, Integer, JSON, String, Text

from .database import Base


class PropertyAd(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    owner_email = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float)
    address = Column(String)
    province = Column(String)
    district = Column(String)
    type = Column(String)
    beds = Column(Integer)
    baths = Column(Integer)
    facilities = Column(JSON)
    images = Column(JSON)
    status = Column(String, default="PENDING")
