from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import auth_util, crud, schemas
from .database import get_db

app = FastAPI(title="CeylonStay Admin Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard/kpis", response_model=schemas.AdminKPIOut)
def get_dashboard_kpis(
    _admin: dict = Depends(auth_util.require_admin_or_super_admin),
    db: Session = Depends(get_db),
):
    return crud.get_admin_kpis(db)


@app.get("/dashboard/overview", response_model=schemas.AdminOverviewOut)
def get_dashboard_overview(
    _admin: dict = Depends(auth_util.require_admin_or_super_admin),
    db: Session = Depends(get_db),
):
    return {
        "kpis": crud.get_admin_kpis(db),
        "recent_ads": crud.get_recent_ads(db, limit=10),
    }


@app.get("/ads")
def get_ads(
    status: str | None = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    _admin: dict = Depends(auth_util.require_admin_or_super_admin),
    db: Session = Depends(get_db),
):
    return crud.list_ads(db, status=status, limit=limit, skip=skip)
