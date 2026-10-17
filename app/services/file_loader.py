import csv
import re
from pathlib import PurePath
from typing import BinaryIO

import pandas as pd

SUPPORTED_EXTENSIONS = {".xlsx", ".csv", ".tsv", ".txt"}

# normalized header (lowercase letters/digits only) -> internal name
COLUMN_MAP = {
    "circlename": "circle",
    "regionname": "region",
    "divisionname": "division",
    "officename": "office_name",
    "pincode": "pincode",
    "officetype": "office_type",
    "delivery": "is_delivery",
    "district": "district",
    "statename": "state",
    "latitude": "latitude",
    "longitude": "longitude",
}
REQUIRED = ["circle", "region", "division", "office_name", "pincode", "office_type", "district", "state"]
TEXT_COLS = ["circle", "region", "division", "office_name", "office_type", "district", "state", "is_delivery"]
NA_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-"}

# India bounding box (includes Andaman & Nicobar and Lakshadweep)
LAT_RANGE = (6.0, 38.0)
LON_RANGE = (68.0, 98.0)


class FileFormatError(ValueError):
    pass


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def _read_delimited(file: BinaryIO) -> pd.DataFrame:
    file.seek(0)
    sample = file.read(65536).decode("utf-8-sig", errors="ignore")
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        sep = ","
    for enc in ("utf-8-sig", "latin-1"):
        file.seek(0)
        try:
            return pd.read_csv(file, sep=sep, dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise FileFormatError("Could not decode file (try saving it as UTF-8)")


def _clean_text(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    return s.mask(s.str.lower().isin(NA_TOKENS))


def load_dataframe(file: BinaryIO, filename: str) -> tuple[pd.DataFrame, int]:
    """Returns (clean dataframe, number of rows whose coordinates were discarded)."""
    ext = PurePath(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FileFormatError("Supported files: .xlsx, .csv, .tsv, .txt")

    try:
        if ext == ".xlsx":
            df = pd.read_excel(file, dtype=str, engine="openpyxl", keep_default_na=False)
        else:
            df = _read_delimited(file)
    except FileFormatError:
        raise
    except Exception as exc:
        raise FileFormatError(f"Could not read file: {exc}") from exc

    df.columns = [COLUMN_MAP.get(_norm(c), _norm(c)) for c in df.columns]
    missing = [c for c in COLUMN_MAP.values() if c not in df.columns]
    if missing:
        raise FileFormatError(f"Missing columns: {', '.join(missing)}")
    df = df[list(COLUMN_MAP.values())].copy()

    for c in TEXT_COLS:
        df[c] = _clean_text(df[c])
    for c in ("state", "district", "office_type"):
        df[c] = df[c].str.upper()

    # pincode: exactly 6 digits, otherwise the row is dropped later
    pin = _clean_text(df["pincode"]).str.replace(r"\.0$", "", regex=True)
    df["pincode"] = pin.where(pin.str.fullmatch(r"\d{6}", na=False))

    df["is_delivery"] = df["is_delivery"].str.lower().eq("delivery")

    # coordinates: keep only valid pairs inside India's bounding box
    raw_lat, raw_lon = _clean_text(df["latitude"]), _clean_text(df["longitude"])
    lat = pd.to_numeric(raw_lat, errors="coerce")
    lon = pd.to_numeric(raw_lon, errors="coerce")
    ok = lat.between(*LAT_RANGE) & lon.between(*LON_RANGE)
    invalid_coords = int(((raw_lat.notna() | raw_lon.notna()) & ~ok).sum())
    df["latitude"] = lat.where(ok).round(7)
    df["longitude"] = lon.where(ok).round(7)

    df = df.astype(object).where(df.notna(), None)
    return df, invalid_coords
