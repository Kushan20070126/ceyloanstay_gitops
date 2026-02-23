from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, geo, models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay Search Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ad_to_out(ad: models.PropertyAd, user_lat: float | None = None, user_lon: float | None = None) -> schemas.AdSearchOut:
    lat, lon = geo.ad_coordinates(ad)
    distance = None
    if user_lat is not None and user_lon is not None:
        distance = round(geo.haversine_km(user_lat, user_lon, lat, lon), 2)

    facilities = ad.facilities if isinstance(ad.facilities, list) else []
    images = ad.images if isinstance(ad.images, list) else []

    return schemas.AdSearchOut(
        id=ad.id,
        title=ad.title,
        description=ad.description,
        price=ad.price,
        address=ad.address,
        province=ad.province,
        district=ad.district,
        type=ad.type,
        beds=ad.beds,
        baths=ad.baths,
        facilities=[str(item) for item in facilities],
        images=[str(item) for item in images],
        status=ad.status,
        latitude=lat,
        longitude=lon,
        distance_km=distance,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ads", response_model=schemas.SearchResponse)
def get_all_ads(
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
    db: Session = Depends(get_db),
):
    ads = crud.list_ads(db, skip=skip, limit=limit, only_active=only_active)
    items = [_ad_to_out(ad) for ad in ads]
    return {"total": len(items), "items": items}


@app.get("/ads/{ad_id}", response_model=schemas.AdSearchOut)
def get_single_ad(ad_id: int, db: Session = Depends(get_db)):
    ad = crud.get_ad(db, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    return _ad_to_out(ad)


@app.get("/ads/search", response_model=schemas.SearchResponse)
def search_ads(
    q: str | None = None,
    district: str | None = None,
    ad_type: str | None = Query(default=None, alias="type"),
    min_price: float | None = None,
    max_price: float | None = None,
    beds: int | None = None,
    baths: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
    db: Session = Depends(get_db),
):
    ads = crud.search_ads(
        db,
        q=q,
        district=district,
        ad_type=ad_type,
        min_price=min_price,
        max_price=max_price,
        beds=beds,
        baths=baths,
        only_active=only_active,
        skip=skip,
        limit=limit,
    )

    items = [_ad_to_out(ad, user_lat=lat, user_lon=lon) for ad in ads]

    if radius_km is not None and lat is not None and lon is not None:
        items = [item for item in items if item.distance_km is not None and item.distance_km <= radius_km]

    return {"total": len(items), "items": items}
