from pydantic import BaseModel


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
