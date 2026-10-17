from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload import UploadResult
from app.services.file_loader import FileFormatError, load_dataframe
from app.services.importer import import_dataframe

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResult)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload .xlsx / .csv / .tsv with columns: circlename, regionname, divisionname, officename,
    pincode, officetype, delivery, district, statename, latitude, longitude."""
    try:
        df, invalid_coords = load_dataframe(file.file, file.filename or "")
    except FileFormatError as exc:
        raise HTTPException(400, str(exc))

    result = import_dataframe(db, df, invalid_coords)
    return UploadResult(filename=file.filename, **result)
