from pydantic import BaseModel


class PostOfficeOut(BaseModel):
    id: int
    office_name: str
    pincode: str
    office_type: str
    is_delivery: bool
    division: str
    region: str
    circle: str
    district: str
    state: str
    latitude: float | None
    longitude: float | None


class NameOut(BaseModel):
    id: int
    name: str
