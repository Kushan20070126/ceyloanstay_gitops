from pydantic import BaseModel, EmailStr, Field


class AdBase(BaseModel):
    title: str = Field(..., example="Luxury Single Room in Malabe")
    description: str = Field(..., example="Close to SLIIT, with attached bathroom")
    price: float = Field(..., gt=0, example=15000.0)
    address: str = Field(..., example="No 45, New Road, Malabe")
    province: str = Field(..., example="Western")
    district: str = Field(..., example="Colombo")
    type: str = Field(..., example="single-room")
    beds: int = Field(default=1, ge=0)
    baths: int = Field(default=1, ge=0)
    facilities: list[str] = Field(default_factory=list, example=["Wifi", "A/C"])


class AdCreate(AdBase):
    pass


class AdUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    status: str | None = None


class AdOut(AdBase):
    id: int
    owner_email: EmailStr
    images: list[str]
    status: str

    class Config:
        from_attributes = True


class AdShortOut(BaseModel):
    id: int
    title: str
    price: float
    district: str
    images: list[str]
    status: str

    class Config:
        from_attributes = True
