import json
import uuid

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import auth_util, cache, crud, rabbitmq
from .database import Base, engine, get_db
from .minio_client import get_object_stream, upload_to_minio

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


@app.get("/ads/{ad_id}")
def get_ad_by_id(ad_id: int, db: Session = Depends(get_db)):
    cache_key = f"ads:{ad_id}"
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    ad = crud.get_ad_by_id(db, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Property not found")

    payload = jsonable_encoder(ad)
    cache.set_json(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


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
