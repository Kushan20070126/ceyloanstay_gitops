from sqlalchemy.orm import Session

from . import models


def create_property_ad(
    db: Session,
    *,
    email: str,
    title: str,
    description: str,
    price: float,
    address: str,
    province: str,
    district: str,
    ad_type: str,
    beds: int,
    baths: int,
    facilities: list[str],
    images: list[str],
) -> models.PropertyAd:
    db_ad = models.PropertyAd(
        owner_email=email,
        title=title,
        description=description,
        price=price,
        address=address,
        province=province,
        district=district,
        type=ad_type,
        beds=beds,
        baths=baths,
        facilities=facilities,
        images=images,
        status="PENDING",
    )
    db.add(db_ad)
    db.commit()
    db.refresh(db_ad)
    return db_ad


def get_ad_by_id(db: Session, ad_id: int) -> models.PropertyAd | None:

    return db.query(models.PropertyAd).filter(models.PropertyAd.id == ad_id).first()


def get_all_active_ads(db: Session, skip: int = 0, limit: int = 100) -> list[models.PropertyAd]:

    return (
        db.query(models.PropertyAd)
        .filter(models.PropertyAd.status == "ACTIVE")
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user_ads(db: Session, email: str) -> list[models.PropertyAd]:

    return db.query(models.PropertyAd).filter(models.PropertyAd.owner_email == email).all()


def update_ad_status(db: Session, ad_id: int, status: str) -> models.PropertyAd | None:

    db_ad = get_ad_by_id(db, ad_id)
    if not db_ad:
        return None

    db_ad.status = status
    db.commit()
    db.refresh(db_ad)

    return db_ad


def delete_ad(db: Session, ad_id: int, email: str) -> bool:

    db_ad = (
        db.query(models.PropertyAd)
        .filter(models.PropertyAd.id == ad_id, models.PropertyAd.owner_email == email)
        .first()
    )
    
    if not db_ad:
        return False

    db.delete(db_ad)
    db.commit()
    return True
