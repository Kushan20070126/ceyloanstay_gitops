from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models


def list_ads(db: Session, skip: int = 0, limit: int = 100, only_active: bool = True) -> list[models.PropertyAd]:
    query = db.query(models.PropertyAd)
    if only_active:
        query = query.filter(models.PropertyAd.status == "ACTIVE")
    return query.offset(skip).limit(limit).all()


def get_ad(db: Session, ad_id: int) -> models.PropertyAd | None:
    return db.query(models.PropertyAd).filter(models.PropertyAd.id == ad_id).first()


def search_ads(
    db: Session,
    *,
    q: str | None = None,
    district: str | None = None,
    ad_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    beds: int | None = None,
    baths: int | None = None,
    only_active: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[models.PropertyAd]:
    query = db.query(models.PropertyAd)

    if only_active:
        query = query.filter(models.PropertyAd.status == "ACTIVE")
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                models.PropertyAd.title.ilike(term),
                models.PropertyAd.description.ilike(term),
                models.PropertyAd.address.ilike(term),
                models.PropertyAd.district.ilike(term),
                models.PropertyAd.province.ilike(term),
            )
        )
    if district:
        query = query.filter(models.PropertyAd.district.ilike(district))
    if ad_type:
        query = query.filter(models.PropertyAd.type.ilike(ad_type))
    if min_price is not None:
        query = query.filter(models.PropertyAd.price >= min_price)
    if max_price is not None:
        query = query.filter(models.PropertyAd.price <= max_price)
    if beds is not None:
        query = query.filter(models.PropertyAd.beds >= beds)
    if baths is not None:
        query = query.filter(models.PropertyAd.baths >= baths)

    return query.offset(skip).limit(limit).all()
