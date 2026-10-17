from pydantic import BaseModel


class DimStats(BaseModel):
    inserted: int = 0


class OfficeStats(BaseModel):
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0


class UploadResult(BaseModel):
    filename: str
    rows_read: int
    rows_skipped: int          # missing required fields / invalid pincode
    duplicates_in_file: int
    invalid_coordinates: int   # lat/long missing-or-out-of-range pairs stored as NULL
    circles: DimStats
    regions: DimStats
    divisions: DimStats
    states: DimStats
    districts: DimStats
    post_offices: OfficeStats
