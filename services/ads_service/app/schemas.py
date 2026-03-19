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
    title: str | None = Field(default=None, example="Updated Luxury Single Room")
    description: str | None = Field(default=None, example="Updated ad description")
    price: float | None = Field(default=None, gt=0, example=17500.0)
    address: str | None = Field(default=None, example="No 48, Main Street, Malabe")
    province: str | None = Field(default=None, example="Western")
    district: str | None = Field(default=None, example="Colombo")
    type: str | None = Field(default=None, example="single-room")
    beds: int | None = Field(default=None, ge=0)
    baths: int | None = Field(default=None, ge=0)
    facilities: list[str] | None = None


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


class DraftAdIn(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    address: str | None = None
    province: str | None = None
    district: str | None = None
    type: str | None = None
    beds: int | None = None
    baths: int | None = None
    facilities: list[str] | None = None
    images: list[str] | None = None
