from textwrap import dedent

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.upload import UploadResult
from app.services.file_loader import FileFormatError, load_dataframe
from app.services.importer import import_dataframe

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = (".xlsx", ".csv", ".tsv")

UPLOAD_DESCRIPTION = dedent("""\
    Upload an `.xlsx`, `.csv` or `.tsv` file to import or update the India Post
    pincode directory.

    ### Required columns

    `circlename`, `regionname`, `divisionname`, `officename`, `pincode`,
    `officetype`, `delivery`, `district`, `statename`, `latitude`, `longitude`

    ### How to get the data

    Use the official **All India Pincode Directory** dataset on the
    [Open Government Data (OGD) Platform India](https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month).

    1. Open the dataset page on data.gov.in.
    2. Sign in or register if the site asks for it before downloading.
    3. Choose the download format (`CSV` or `XLS`).
    4. Download the file, or generate an API/export link if you want a filtered copy.
    5. Check that the column names match the list above.
    6. Upload the file here.

    ### Notes

    - Rows with missing or out-of-range latitude/longitude are still imported;
      their coordinates are reported as invalid in the response.
    - Existing records are updated and new ones are inserted (upsert).
""")


@router.post(
    "",
    response_model=UploadResult,
    summary="Upload India Post pincode directory file",
    description=UPLOAD_DESCRIPTION,
    responses={400: {"description": "Invalid file type or missing/incorrect columns"}},
)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .csv or .tsv files are supported")

    try:
        df, invalid_coords = load_dataframe(file.file, filename)
    except FileFormatError as exc:
        raise HTTPException(400, str(exc))

    result = import_dataframe(db, df, invalid_coords)
    return UploadResult(filename=filename, **result)