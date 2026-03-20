from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
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


@app.get("/facilities", response_model=list[str])
def get_facilities(
    db: Session = Depends(get_db),
):
    facilities = crud.list_facilities(db)
    return [item["name"] for item in facilities]


@app.post("/facilities", response_model=schemas.FacilityUpsertOut)
def create_facility(
    facility_in: schemas.FacilityCreateIn,
    response: Response,
    _admin: dict = Depends(auth_util.require_admin_or_super_admin),
    db: Session = Depends(get_db),
):
    try:
        facility, created = crud.create_facility(db, facility_in.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return {**facility, "created": created}
