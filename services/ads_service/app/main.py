import json
import threading
import uuid

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import auth_util, cache, crud, rabbitmq, schemas
from .database import Base, SessionLocal, engine, get_db
from .minio_client import delete_object, get_object_stream, upload_to_minio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay Ads Service")
CACHE_TTL_SECONDS = 120

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def parse_facilities(raw_facilities: str) -> list[str]:
    if not raw_facilities:
        return []

    try:
        parsed = json.loads(raw_facilities)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass

    return [item.strip() for item in raw_facilities.split(",") if item.strip()]


async def upload_images(images: list[UploadFile]) -> list[str]:

    uploaded_names: list[str] = []
    
    for image in images:
        extension = image.filename.split(".")[-1] if image.filename and "." in image.filename else "jpg"
        unique_name = f"{uuid.uuid4()}.{extension}"
        content = await image.read()
        try:
            upload_to_minio(content, unique_name, image.content_type or "image/jpeg")
            uploaded_names.append(unique_name)
        except Exception as error:
            print(f"MinIO Upload Error: {error}")
            raise HTTPException(status_code=500, detail="Failed to upload image")
    return uploaded_names


def delete_images(image_names: list[str]) -> None:
    for image_name in image_names:
        try:
            delete_object(image_name)
        except Exception as error:
            print(f"MinIO Delete Error for {image_name}: {error}")


def process_user_event(payload: dict) -> None:
    event = str(payload.get("event", "")).lower()
    user_email = payload.get("email")
    if not user_email:
        return

    db = SessionLocal()
    try:
        if event == "user_deactivated":
            updated_count = crud.deactivate_ads_by_owner(db, str(user_email), status="INACTIVE")
            if updated_count:
                cache.delete("ads:active")
                cache.delete_by_pattern("ads:*")
        elif event == "user_deleted":
            deleted_images = crud.delete_ads_by_owner_and_return_images(db, str(user_email))
            if deleted_images:
                delete_images(deleted_images)
            cache.delete("ads:active")
            cache.delete_by_pattern("ads:*")
    finally:
        db.close()


@app.on_event("startup")
def start_user_event_consumer() -> None:
    worker = threading.Thread(
        target=rabbitmq.consume_user_events,
        args=(process_user_event,),
        daemon=True,
    )
    worker.start()


@app.post("/ads")
async def create_ad(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    address: str = Form(...),
    province: str = Form(...),
    district: str = Form(...),
    type: str = Form(...),
    beds: int = Form(...),
    baths: int = Form(...),
    facilities: str = Form(...),
    images: list[UploadFile] = File(...),
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    uploaded_filenames = await upload_images(images)
    parsed_facilities = parse_facilities(facilities)

    new_ad = crud.create_property_ad(
        db,
        email=email,
        title=title,
        description=description,
        price=price,
        address=address,
        province=province,
        district=district,
        ad_type=type,
        beds=beds,
        baths=baths,
        facilities=parsed_facilities,
        images=uploaded_filenames,
    )

    rabbitmq.send_to_ai_queue(new_ad.id, uploaded_filenames, email)
    rabbitmq.send_notification_event(
        user_email=email,
        ad_id=new_ad.id,
        message="Your ad was created and sent for AI image verification.",
    )
    cache.delete("ads:active")

    return {
        "status": "success",
        "message": "Ad submitted for AI verification",
        "ad_id": new_ad.id,
    }


@app.get("/ads/active")
def get_active_ads(db: Session = Depends(get_db)):
    cache_key = "ads:active"
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    ads = crud.get_all_active_ads(db)
    payload = jsonable_encoder(ads)
    cache.set_json(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


@app.get("/ads/me")
def get_my_ads(
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    return crud.get_user_ads(db, email)


@app.get("/ads/{ad_id:int}")
def get_ad_by_id(ad_id: int, request: Request, db: Session = Depends(get_db)):
    cache_key = f"ads:{ad_id}"
    cached = cache.get_json(cache_key)
    if cached is not None:
        if cached.get("status") == "ACTIVE":
            return cached
        viewer = auth_util.get_optional_user_email_from_assertion(request.headers.get("X-User-Email"))
        if viewer and cached.get("owner_email") == viewer:
            return cached
        raise HTTPException(status_code=403, detail="Only owner can view this ad")

    ad = crud.get_ad_by_id(db, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Property not found")
    if ad.status != "ACTIVE":
        viewer = auth_util.get_optional_user_email_from_assertion(request.headers.get("X-User-Email"))
        if not viewer or viewer != ad.owner_email:
            raise HTTPException(status_code=403, detail="Only owner can view this ad")

    payload = jsonable_encoder(ad)
    cache.set_json(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


@app.put("/ads/{ad_id:int}")
def update_ad(
    ad_id: int,
    ad_data: schemas.AdUpdate,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    updates = ad_data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    if "facilities" in updates and updates["facilities"] is not None:
        updates["facilities"] = [str(item).strip() for item in updates["facilities"] if str(item).strip()]

    updated_ad = crud.update_ad(db, ad_id, email, updates)
    if not updated_ad:
        raise HTTPException(status_code=404, detail="Ad not found or access denied")

    cache.delete("ads:active")
    cache.delete(f"ads:{ad_id}")

    return {
        "status": "success",
        "message": "Ad updated successfully",
        "ad_id": ad_id,
    }


@app.patch("/ads/{ad_id:int}/deactivate")
def deactivate_ad(
    ad_id: int,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    deactivated_ad = crud.deactivate_ad(db, ad_id, email)
    if not deactivated_ad:
        raise HTTPException(status_code=404, detail="Ad not found or access denied")

    cache.delete("ads:active")
    cache.delete(f"ads:{ad_id}")

    rabbitmq.send_notification_event(
        user_email=email,
        ad_id=ad_id,
        message="Your ad was deactivated successfully.",
    )

    return {
        "status": "success",
        "message": "Ad deactivated successfully",
        "ad_id": ad_id,
    }


@app.post("/ads/draft")
def create_draft_ad(
    draft_data: schemas.DraftAdIn,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    draft = crud.create_draft_ad(
        db,
        owner_email=email,
        title=draft_data.title,
        description=draft_data.description,
        price=draft_data.price,
        address=draft_data.address,
        province=draft_data.province,
        district=draft_data.district,
        ad_type=draft_data.type,
        beds=draft_data.beds,
        baths=draft_data.baths,
        facilities=draft_data.facilities,
        images=draft_data.images,
    )
    return {"status": "success", "message": "Draft saved", "ad_id": draft.id}


@app.put("/ads/draft/{ad_id}")
def update_draft_ad(
    ad_id: int,
    draft_data: schemas.DraftAdIn,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    updated = crud.update_draft_ad(db, ad_id, email, draft_data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Draft not found or cannot update")
    cache.delete(f"ads:{ad_id}")
    return {"status": "success", "message": "Draft updated", "ad_id": ad_id}


@app.post("/ads/draft/{ad_id}/publish")
def publish_draft_ad(
    ad_id: int,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    ad = crud.publish_draft_ad(db, ad_id, email)
    if not ad:
        raise HTTPException(status_code=404, detail="Draft not found or cannot publish")

    images = ad.images if isinstance(ad.images, list) else []
    rabbitmq.send_to_ai_queue(ad.id, [str(item) for item in images], email)
    rabbitmq.send_notification_event(
        user_email=email,
        ad_id=ad.id,
        message="Your draft ad was published and sent for AI image verification.",
    )
    cache.delete("ads:active")
    cache.delete(f"ads:{ad_id}")
    return {"status": "success", "message": "Draft published", "ad_id": ad_id}


@app.delete("/ads/{ad_id}")
def delete_ad(
    ad_id: int,
    email: str = Depends(auth_util.get_current_user_email),
    db: Session = Depends(get_db),
):
    deleted_images = crud.delete_ad_and_return_images(db, ad_id, email)
    if deleted_images is None:
        raise HTTPException(status_code=404, detail="Ad not found or access denied")

    delete_images(deleted_images)
    cache.delete("ads:active")
    cache.delete(f"ads:{ad_id}")

    return {
        "status": "success",
        "message": "Ad deleted successfully",
        "ad_id": ad_id,
    }


@app.get("/ads/image/{image_name}")
async def get_ad_image(image_name: str):
    try:
        response = get_object_stream(image_name)

        def iter_file():
            yield from response.stream(32 * 1024)
            response.close()
            response.release_conn()

        return StreamingResponse(
            iter_file(),
            media_type="image/jpeg",
        )
    except Exception as error:
        print(f"MinIO Error for {image_name}: {error}")
        raise HTTPException(status_code=404, detail=f"Image {image_name} not found")
