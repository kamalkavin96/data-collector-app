from pydantic import BaseModel


class TableStats(BaseModel):
    inserted: int = 0
    updated: int = 0


class UploadResult(BaseModel):
    filename: str
    rows_read: int
    rows_skipped: int
    states: TableStats
    districts: TableStats
    sub_districts: TableStats
    villages: TableStats
