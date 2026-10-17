import pandas as pd
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Circle, District, Division, PostOffice, Region, State
from app.services.file_loader import REQUIRED


def _chunks(rows: list[dict]):
    for i in range(0, len(rows), settings.CHUNK_SIZE):
        yield rows[i : i + settings.CHUNK_SIZE]


def _insert_dim(db: Session, model, rows: list[dict], conflict_cols: list[str]) -> dict:
    """Insert new dimension rows; existing ones are left alone (their name IS the key)."""
    inserted = 0
    for chunk in _chunks(rows):
        stmt = insert(model).values(chunk).on_conflict_do_nothing(index_elements=conflict_cols)
        inserted += len(db.execute(stmt.returning(model.id)).all())
    return {"inserted": inserted}


def _upsert_offices(db: Session, rows: list[dict]) -> dict:
    """Upsert on the natural key. Rows whose data did not change are NOT rewritten,
    so updated_at only moves when something really changed."""
    inserted = updated = 0
    t = PostOffice
    for chunk in _chunks(rows):
        stmt = insert(t).values(chunk)
        ex = stmt.excluded
        changed = or_(
            t.office_type.is_distinct_from(ex.office_type),
            t.is_delivery.is_distinct_from(ex.is_delivery),
            t.district_id.is_distinct_from(ex.district_id),
            t.latitude.is_distinct_from(ex.latitude),
            t.longitude.is_distinct_from(ex.longitude),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_office_pincode_name_division",
            set_={
                "office_type": ex.office_type,
                "is_delivery": ex.is_delivery,
                "district_id": ex.district_id,
                "latitude": ex.latitude,
                "longitude": ex.longitude,
                "updated_at": func.now(),
            },
            where=changed,
        ).returning(literal_column("(xmax = 0)"))  # true = fresh insert, false = update
        flags = db.execute(stmt).scalars().all()
        inserted += sum(flags)
        updated += len(flags) - sum(flags)
    return {"inserted": inserted, "updated": updated, "unchanged": len(rows) - inserted - updated}


def import_dataframe(db: Session, df: pd.DataFrame, invalid_coords: int) -> dict:
    rows_read = len(df)
    df = df.dropna(subset=REQUIRED)
    rows_skipped = rows_read - len(df)

    try:
        # Circles
        stats_circles = _insert_dim(
            db, Circle, [{"name": n} for n in df["circle"].unique()], ["name"]
        )
        circle_map = dict(db.execute(select(Circle.name, Circle.id)).all())

        # Regions
        pairs = df[["circle", "region"]].drop_duplicates()
        stats_regions = _insert_dim(
            db, Region,
            [{"circle_id": circle_map[c], "name": r} for c, r in pairs.itertuples(index=False)],
            ["circle_id", "name"],
        )
        region_map = {(c, n): i for c, n, i in db.execute(select(Region.circle_id, Region.name, Region.id))}

        # Divisions
        triples = df[["circle", "region", "division"]].drop_duplicates()
        stats_divisions = _insert_dim(
            db, Division,
            [
                {"region_id": region_map[(circle_map[c], r)], "name": d}
                for c, r, d in triples.itertuples(index=False)
            ],
            ["region_id", "name"],
        )
        division_map = {(r, n): i for r, n, i in db.execute(select(Division.region_id, Division.name, Division.id))}

        # States
        stats_states = _insert_dim(db, State, [{"name": n} for n in df["state"].unique()], ["name"])
        state_map = dict(db.execute(select(State.name, State.id)).all())

        # Districts
        sd = df[["state", "district"]].drop_duplicates()
        stats_districts = _insert_dim(
            db, District,
            [{"state_id": state_map[s], "name": d} for s, d in sd.itertuples(index=False)],
            ["state_id", "name"],
        )
        district_map = {(s, n): i for s, n, i in db.execute(select(District.state_id, District.name, District.id))}

        # Post offices (dedupe on the natural key, last occurrence wins)
        unique_rows: dict[tuple, dict] = {}
        for r in df.itertuples(index=False):
            division_id = division_map[(region_map[(circle_map[r.circle], r.region)], r.division)]
            unique_rows[(r.pincode, r.office_name, division_id)] = {
                "office_name": r.office_name,
                "pincode": r.pincode,
                "office_type": r.office_type,
                "is_delivery": r.is_delivery,
                "division_id": division_id,
                "district_id": district_map[(state_map[r.state], r.district)],
                "latitude": r.latitude,
                "longitude": r.longitude,
            }
        rows = list(unique_rows.values())
        stats_offices = _upsert_offices(db, rows)

        db.commit()  # all-or-nothing
    except Exception:
        db.rollback()
        raise

    return {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "duplicates_in_file": len(df) - len(rows),
        "invalid_coordinates": invalid_coords,
        "circles": stats_circles,
        "regions": stats_regions,
        "divisions": stats_divisions,
        "states": stats_states,
        "districts": stats_districts,
        "post_offices": stats_offices,
    }
