from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload import UploadResult
from app.services.excel_import import ExcelFormatError, import_dataframe, load_dataframe

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResult)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload an .xlsx or .csv with columns: State Code, State Name, District Code, District Name,
    SubDistrict Code, SubDistrict Name, Village Code, Village Name, Pincode."""
    try:
        df = load_dataframe(file.file, file.filename or "")
    except ExcelFormatError as exc:
        raise HTTPException(400, str(exc))

    result = import_dataframe(db, df)
    return UploadResult(filename=file.filename, **result)
