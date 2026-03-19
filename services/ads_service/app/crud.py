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


def get_owner_ad_by_id(db: Session, ad_id: int, owner_email: str) -> models.PropertyAd | None:
    return (
        db.query(models.PropertyAd)
        .filter(models.PropertyAd.id == ad_id, models.PropertyAd.owner_email == owner_email)
        .first()
    )


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


def create_draft_ad(
    db: Session,
    *,
    owner_email: str,
    title: str | None = None,
    description: str | None = None,
    price: float | None = None,
    address: str | None = None,
    province: str | None = None,
    district: str | None = None,
    ad_type: str | None = None,
    beds: int | None = None,
    baths: int | None = None,
    facilities: list[str] | None = None,
    images: list[str] | None = None,
) -> models.PropertyAd:
    draft = models.PropertyAd(
        owner_email=owner_email,
        title=title or "Untitled Draft",
        description=description,
        price=price,
        address=address,
        province=province,
        district=district,
        type=ad_type,
        beds=beds,
        baths=baths,
        facilities=facilities or [],
        images=images or [],
        status="DRAFT",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def update_draft_ad(
    db: Session,
    ad_id: int,
    owner_email: str,
    updates: dict,
) -> models.PropertyAd | None:
    ad = get_owner_ad_by_id(db, ad_id, owner_email)
    if not ad:
        return None
    if ad.status != "DRAFT":
        return None

    field_map = {
        "title": "title",
        "description": "description",
        "price": "price",
        "address": "address",
        "province": "province",
        "district": "district",
        "type": "type",
        "beds": "beds",
        "baths": "baths",
        "facilities": "facilities",
        "images": "images",
    }
    for req_key, model_key in field_map.items():
        if req_key in updates:
            setattr(ad, model_key, updates[req_key])

    if not ad.title:
        ad.title = "Untitled Draft"

    db.commit()
    db.refresh(ad)
    return ad


def publish_draft_ad(db: Session, ad_id: int, owner_email: str) -> models.PropertyAd | None:
    ad = get_owner_ad_by_id(db, ad_id, owner_email)
    if not ad:
        return None
    if ad.status != "DRAFT":
        return None

    ad.status = "PENDING"
    if not ad.title:
        ad.title = "Untitled Draft"
    if ad.facilities is None:
        ad.facilities = []
    if ad.images is None:
        ad.images = []

    db.commit()
    db.refresh(ad)
    return ad


def update_ad_status(db: Session, ad_id: int, status: str) -> models.PropertyAd | None:

    db_ad = get_ad_by_id(db, ad_id)
    if not db_ad:
        return None

    db_ad.status = status
    db.commit()
    db.refresh(db_ad)

    return db_ad


def update_ad(
    db: Session,
    ad_id: int,
    owner_email: str,
    updates: dict,
) -> models.PropertyAd | None:
    ad = get_owner_ad_by_id(db, ad_id, owner_email)
    if not ad:
        return None

    field_map = {
        "title": "title",
        "description": "description",
        "price": "price",
        "address": "address",
        "province": "province",
        "district": "district",
        "type": "type",
        "beds": "beds",
        "baths": "baths",
        "facilities": "facilities",
    }

    for req_key, model_key in field_map.items():
        if req_key in updates:
            setattr(ad, model_key, updates[req_key])

    db.commit()
    db.refresh(ad)
    return ad


def deactivate_ad(
    db: Session,
    ad_id: int,
    owner_email: str,
    status: str = "INACTIVE",
) -> models.PropertyAd | None:
    ad = get_owner_ad_by_id(db, ad_id, owner_email)
    if not ad:
        return None

    ad.status = status
    db.commit()
    db.refresh(ad)
    return ad


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


def delete_ad_and_return_images(db: Session, ad_id: int, email: str) -> list[str] | None:
    db_ad = (
        db.query(models.PropertyAd)
        .filter(models.PropertyAd.id == ad_id, models.PropertyAd.owner_email == email)
        .first()
    )
    if not db_ad:
        return None

    images = db_ad.images if isinstance(db_ad.images, list) else []
    image_names = [str(image) for image in images]
    db.delete(db_ad)
    db.commit()
    return image_names


def deactivate_ads_by_owner(db: Session, email: str, status: str = "INACTIVE") -> int:
    ads = db.query(models.PropertyAd).filter(models.PropertyAd.owner_email == email).all()
    if not ads:
        return 0

    for ad in ads:
        ad.status = status

    db.commit()
    return len(ads)


def delete_ads_by_owner_and_return_images(db: Session, email: str) -> list[str]:
    ads = db.query(models.PropertyAd).filter(models.PropertyAd.owner_email == email).all()
    if not ads:
        return []

    image_names: list[str] = []
    for ad in ads:
        if isinstance(ad.images, list):
            image_names.extend(str(image) for image in ad.images)
        db.delete(ad)

    db.commit()
    return image_names
