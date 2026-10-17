from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Circle, District, Division, PostOffice, Region, State
from app.schemas.postal import NameOut, PostOfficeOut

router = APIRouter(tags=["post offices"])


def _office_query():
    return (
        select(
            PostOffice.id, PostOffice.office_name, PostOffice.pincode, PostOffice.office_type,
            PostOffice.is_delivery, Division.name.label("division"), Region.name.label("region"),
            Circle.name.label("circle"), District.name.label("district"), State.name.label("state"),
            PostOffice.latitude, PostOffice.longitude,
        )
        .select_from(PostOffice)
        .join(Division, PostOffice.division_id == Division.id)
        .join(Region, Division.region_id == Region.id)
        .join(Circle, Region.circle_id == Circle.id)
        .join(District, PostOffice.district_id == District.id)
        .join(State, District.state_id == State.id)
    )


@router.get("/pincodes/{pincode}", response_model=list[PostOfficeOut])
def offices_by_pincode(pincode: str, db: Session = Depends(get_db)):
    q = _office_query().where(PostOffice.pincode == pincode).order_by(PostOffice.office_name)
    return db.execute(q).mappings().all()


@router.get("/post-offices", response_model=list[PostOfficeOut])
def search_post_offices(
    pincode: str | None = None,
    state: str | None = None,
    district: str | None = None,
    office_type: str | None = Query(None, description="HO / SO / BO"),
    delivery: bool | None = None,
    q: str | None = Query(None, description="office name contains"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = _office_query()
    if pincode:
        query = query.where(PostOffice.pincode == pincode)
    if state:
        query = query.where(State.name == state.strip().upper())
    if district:
        query = query.where(District.name == district.strip().upper())
    if office_type:
        query = query.where(PostOffice.office_type == office_type.strip().upper())
    if delivery is not None:
        query = query.where(PostOffice.is_delivery == delivery)
    if q:
        query = query.where(PostOffice.office_name.ilike(f"%{q.strip()}%"))
    query = query.order_by(PostOffice.id).limit(limit).offset(offset)
    return db.execute(query).mappings().all()


@router.get("/states", response_model=list[NameOut])
def list_states(db: Session = Depends(get_db)):
    return db.execute(select(State.id, State.name).order_by(State.name)).mappings().all()


@router.get("/districts", response_model=list[NameOut])
def list_districts(state: str | None = None, db: Session = Depends(get_db)):
    q = select(District.id, District.name).order_by(District.name)
    if state:
        q = q.join(State, District.state_id == State.id).where(State.name == state.strip().upper())
    return db.execute(q).mappings().all()
