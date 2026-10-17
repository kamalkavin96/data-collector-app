from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index,
    Integer, Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------- Postal hierarchy: Circle -> Region -> Division -> Post Office ----------
class Circle(TimestampMixin, Base):
    __tablename__ = "circles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Region(TimestampMixin, Base):
    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("circle_id", "name", name="uq_region_circle_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Division(TimestampMixin, Base):
    __tablename__ = "divisions"
    __table_args__ = (UniqueConstraint("region_id", "name", name="uq_division_region_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


# ---------- Geography: State -> District ----------
class State(TimestampMixin, Base):
    __tablename__ = "states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class District(TimestampMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("state_id", "name", name="uq_district_state_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


# ---------- Fact table ----------
class PostOffice(TimestampMixin, Base):
    __tablename__ = "post_offices"
    __table_args__ = (
        # Natural key used for upserts; its leading column also serves pincode lookups
        UniqueConstraint("pincode", "office_name", "division_id", name="uq_office_pincode_name_division"),
        CheckConstraint("pincode ~ '^[0-9]{6}$'", name="ck_office_pincode_format"),
        Index("ix_post_offices_district_id", "district_id"),
        Index("ix_post_offices_division_id", "division_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    office_name: Mapped[str] = mapped_column(String(150), nullable=False)
    pincode: Mapped[str] = mapped_column(String(6), nullable=False)
    office_type: Mapped[str] = mapped_column(String(10), nullable=False)  # HO / SO / BO ...
    is_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"), nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
