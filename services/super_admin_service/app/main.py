from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import auth_util, crud, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CeylonStay Super Admin Service")

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


@app.get("/dashboard/kpis", response_model=schemas.SuperAdminKPIOut)
def get_super_dashboard(
    _super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    return crud.get_super_admin_kpis(db)


@app.get("/admins", response_model=list[schemas.AdminAccountOut])
def get_admins(
    _super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    return crud.list_admins(db)


@app.post("/admins", response_model=schemas.AdminAccountOut)
def add_admin(
    payload: schemas.AdminAccountCreate,
    super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        return crud.create_admin(
            db,
            email=str(payload.email),
            role=payload.role,
            created_by=super_admin["email"],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.patch("/admins/{admin_id}/activate", response_model=schemas.AdminAccountOut)
def activate_admin(
    admin_id: int,
    _super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    row = crud.set_admin_status(db, admin_id, True)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")
    return row


@app.patch("/admins/{admin_id}/deactivate", response_model=schemas.AdminAccountOut)
def deactivate_admin(
    admin_id: int,
    _super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    row = crud.set_admin_status(db, admin_id, False)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")
    return row


@app.delete("/admins/{admin_id}")
def remove_admin(
    admin_id: int,
    _super_admin: dict = Depends(auth_util.require_super_admin),
    db: Session = Depends(get_db),
):
    ok = crud.delete_admin(db, admin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"status": "success", "message": "Admin removed"}
