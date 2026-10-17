from pathlib import PurePath
import re
from typing import BinaryIO

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import District, State, SubDistrict, Village

# normalized header (lowercase, letters/digits only) -> internal name
COLUMN_MAP = {
    "statecode": "state_code",
    "statename": "state_name",
    "districtcode": "district_code",
    "districtname": "district_name",
    "subdistrictcode": "sub_district_code",
    "subdistrictname": "sub_district_name",
    "villagecode": "village_code",
    "villagename": "village_name",
    "pincode": "pincode",
}
REQUIRED = [c for c in COLUMN_MAP.values() if c != "pincode"]


class ExcelFormatError(ValueError):
    pass


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}


def _read_csv(file: BinaryIO) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        file.seek(0)
        try:
            return pd.read_csv(file, dtype=str, encoding=encoding, skipinitialspace=True)
        except UnicodeDecodeError:
            continue
    raise ExcelFormatError("Could not decode CSV file (try saving it as UTF-8)")


def load_dataframe(file: BinaryIO, filename: str) -> pd.DataFrame:
    ext = PurePath(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ExcelFormatError("Only .xlsx and .csv files are supported")

    try:
        if ext == ".csv":
            df = _read_csv(file)
        else:
            df = pd.read_excel(file, dtype=str, engine="openpyxl")
    except ExcelFormatError:
        raise
    except Exception as exc:  # corrupt / wrong format
        raise ExcelFormatError(f"Could not read file: {exc}") from exc

    df.columns = [COLUMN_MAP.get(_norm(c), _norm(c)) for c in df.columns]
    missing = [c for c in COLUMN_MAP.values() if c not in df.columns]
    if missing:
        raise ExcelFormatError(f"Missing columns: {', '.join(missing)}")

    df = df[list(COLUMN_MAP.values())]
    df = df.apply(lambda s: s.str.strip())
    df = df.replace({"": None}).astype(object)
    df = df.where(df.notna(), None)
    return df


def _upsert(db: Session, model, rows: list[dict], key: str, update_cols: list[str]) -> dict:
    """Bulk insert-or-update on a unique `key` column. Returns inserted/updated counts."""
    if not rows:
        return {"inserted": 0, "updated": 0}

    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError(f"Upsert not implemented for dialect '{dialect}'")

    col = getattr(model, key)
    existing = set(db.scalars(select(col)))
    updated = sum(1 for r in rows if r[key] in existing)

    for i in range(0, len(rows), settings.CHUNK_SIZE):
        chunk = rows[i : i + settings.CHUNK_SIZE]
        stmt = insert(model).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[key],
            set_={**{c: stmt.excluded[c] for c in update_cols}, "updated_at": func.now()},
        )
        db.execute(stmt)

    return {"inserted": len(rows) - updated, "updated": updated}


def _id_map(db: Session, model, key: str) -> dict[str, int]:
    return {code: id_ for code, id_ in db.execute(select(getattr(model, key), model.id))}


def import_dataframe(db: Session, df: pd.DataFrame) -> dict:
    rows_read = len(df)
    df = df.dropna(subset=REQUIRED)
    rows_skipped = rows_read - len(df)

    try:
        # 1. States
        states = df[["state_code", "state_name"]].drop_duplicates("state_code", keep="last")
        s_stats = _upsert(db, State, states.to_dict("records"), "state_code", ["state_name"])
        state_map = _id_map(db, State, "state_code")

        # 2. Districts
        d = df[["district_code", "district_name", "state_code"]].drop_duplicates("district_code", keep="last")
        d_rows = [
            {"district_code": r.district_code, "district_name": r.district_name, "state_id": state_map[r.state_code]}
            for r in d.itertuples(index=False)
        ]
        d_stats = _upsert(db, District, d_rows, "district_code", ["district_name", "state_id"])
        district_map = _id_map(db, District, "district_code")

        # 3. Sub-districts
        sd = df[["sub_district_code", "sub_district_name", "district_code"]].drop_duplicates(
            "sub_district_code", keep="last"
        )
        sd_rows = [
            {
                "sub_district_code": r.sub_district_code,
                "sub_district_name": r.sub_district_name,
                "district_id": district_map[r.district_code],
            }
            for r in sd.itertuples(index=False)
        ]
        sd_stats = _upsert(
            db, SubDistrict, sd_rows, "sub_district_code", ["sub_district_name", "district_id"]
        )
        sub_map = _id_map(db, SubDistrict, "sub_district_code")

        # 4. Villages (with pincode)
        v = df[["village_code", "village_name", "pincode", "sub_district_code"]].drop_duplicates(
            "village_code", keep="last"
        )
        v_rows = [
            {
                "village_code": r.village_code,
                "village_name": r.village_name,
                "pincode": r.pincode,
                "sub_district_id": sub_map[r.sub_district_code],
            }
            for r in v.itertuples(index=False)
        ]
        v_stats = _upsert(
            db, Village, v_rows, "village_code", ["village_name", "pincode", "sub_district_id"]
        )

        db.commit()  # all-or-nothing
    except Exception:
        db.rollback()
        raise

    return {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "states": s_stats,
        "districts": d_stats,
        "sub_districts": sd_stats,
        "villages": v_stats,
    }
