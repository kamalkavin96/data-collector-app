from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class State(TimestampMixin, Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    state_name: Mapped[str] = mapped_column(String(255), nullable=False)

    districts: Mapped[list["District"]] = relationship(back_populates="state")


class District(TimestampMixin, Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    district_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True, nullable=False)

    state: Mapped[State] = relationship(back_populates="districts")
    sub_districts: Mapped[list["SubDistrict"]] = relationship(back_populates="district")


class SubDistrict(TimestampMixin, Base):
    __tablename__ = "sub_districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sub_district_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    sub_district_name: Mapped[str] = mapped_column(String(255), nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True, nullable=False)

    district: Mapped[District] = relationship(back_populates="sub_districts")
    villages: Mapped[list["Village"]] = relationship(back_populates="sub_district")


class Village(TimestampMixin, Base):
    __tablename__ = "villages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    village_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    sub_district_id: Mapped[int] = mapped_column(ForeignKey("sub_districts.id"), index=True, nullable=False)

    sub_district: Mapped[SubDistrict] = relationship(back_populates="villages")
