from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class StateOut(_Base):
    state_code: str
    state_name: str


class DistrictOut(_Base):
    district_code: str
    district_name: str
    state_id: int


class SubDistrictOut(_Base):
    sub_district_code: str
    sub_district_name: str
    district_id: int


class VillageOut(_Base):
    village_code: str
    village_name: str
    pincode: str | None
    sub_district_id: int
