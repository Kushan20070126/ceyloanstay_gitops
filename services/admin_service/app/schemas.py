from pydantic import BaseModel, Field


class AdminKPIOut(BaseModel):
    total_ads: int
    active_ads: int
    pending_ads: int
    rejected_ads: int
    draft_ads: int
    total_clicks: int
    total_notifications: int
    unread_notifications: int


class AdminOverviewOut(BaseModel):
    kpis: AdminKPIOut
    recent_ads: list[dict]


class FacilityCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, example="Wifi")


class FacilityOut(BaseModel):
    id: int
    name: str


class FacilityUpsertOut(FacilityOut):
    created: bool
