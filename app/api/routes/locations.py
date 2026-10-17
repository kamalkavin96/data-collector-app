from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import District, State, SubDistrict, Village
from app.schemas.location import DistrictOut, StateOut, SubDistrictOut, VillageOut

router = APIRouter(tags=["locations"])


@router.get("/states", response_model=list[StateOut])
def list_states(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return db.scalars(select(State).order_by(State.id).offset(skip).limit(limit)).all()


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(
    state_code: str | None = None,
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    q = select(District).order_by(District.id)
    if state_code:
        q = q.join(State).where(State.state_code == state_code)
    return db.scalars(q.offset(skip).limit(limit)).all()


@router.get("/sub-districts", response_model=list[SubDistrictOut])
def list_sub_districts(
    district_code: str | None = None,
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    q = select(SubDistrict).order_by(SubDistrict.id)
    if district_code:
        q = q.join(District).where(District.district_code == district_code)
    return db.scalars(q.offset(skip).limit(limit)).all()


@router.get("/villages", response_model=list[VillageOut])
def list_villages(
    sub_district_code: str | None = None,
    pincode: str | None = None,
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    q = select(Village).order_by(Village.id)
    if sub_district_code:
        q = q.join(SubDistrict).where(SubDistrict.sub_district_code == sub_district_code)
    if pincode:
        q = q.where(Village.pincode == pincode)
    return db.scalars(q.offset(skip).limit(limit)).all()
