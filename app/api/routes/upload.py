from textwrap import dedent

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload import UploadResult
from app.services.excel_import import ExcelFormatError, import_dataframe, load_dataframe

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = (".xlsx", ".csv")

UPLOAD_DESCRIPTION = dedent("""\
    Upload an `.xlsx` or `.csv` file to import or update location directory records.

    ### Required columns

    `State Code`, `State Name`, `District Code`, `District Name`,
    `SubDistrict Code`, `SubDistrict Name`, `Village Code`, `Village Name`, `Pincode`

    ### How to get the data

    Use the official Government of India
    [Local Government Directory (LGD)](https://lgdirectory.gov.in/downloadDirectory.do).

    1. Open the LGD **Download Directory** page.
    2. Select the required download criteria.
    3. Choose the directory entity (State, District, Sub-District, Village or Development Block).
    4. Select the state and any other applicable filters.
    5. Choose the output format (`.xlsx` or `.csv`).
    6. Complete the CAPTCHA and generate the report.
    7. Download the file and upload it here.

    **Note:** Existing records are updated and new ones are inserted (upsert).
""")


@router.post(
    "",
    response_model=UploadResult,
    summary="Upload location directory file",
    description=UPLOAD_DESCRIPTION,
    responses={400: {"description": "Invalid file type or missing/incorrect columns"}},
)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx or .csv files are supported")

    try:
        df = load_dataframe(file.file, filename)
    except ExcelFormatError as exc:
        raise HTTPException(400, str(exc))

    result = import_dataframe(db, df)
    return UploadResult(filename=filename, **result)