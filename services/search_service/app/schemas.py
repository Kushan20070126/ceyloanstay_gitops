from pydantic import BaseModel


class AdSearchOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    price: float | None = None
    address: str | None = None
    province: str | None = None
    district: str | None = None
    type: str | None = None
    beds: int | None = None
    baths: int | None = None
    facilities: list[str] = []
    images: list[str] = []
    status: str | None = None
    latitude: float
    longitude: float
    distance_km: float | None = None


class SearchResponse(BaseModel):
    total: int
    items: list[AdSearchOut]
