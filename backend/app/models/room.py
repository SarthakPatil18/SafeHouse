"""SQLAlchemy models for rooms and room environmental baselines."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.alert import Alert, Anomaly
    from app.models.patrol import PatrolStop
    from app.models.reading import SensorReading


class Room(Base):
    """Represents a physical room or waypoint for rover patrol."""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        doc="Unique room identifier (e.g., room_1, room_4, or UUID)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable room name (e.g., Bedroom 1, Kitchen)",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Room type category (e.g. bedroom, kitchen, living_room, hallway)",
    )
    x: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Spatial X-coordinate waypoint on map",
    )
    y: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Spatial Y-coordinate waypoint on map",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Default patrol visitation sequence order",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this room is included in active patrol routes",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Creation timestamp in UTC",
    )

    # Relationships
    baseline: Mapped[Optional["RoomBaseline"]] = relationship(
        "RoomBaseline",
        back_populates="room",
        uselist=False,
        cascade="all, delete-orphan",
    )
    readings: Mapped[List["SensorReading"]] = relationship(
        "SensorReading",
        back_populates="room",
    )
    anomalies: Mapped[List["Anomaly"]] = relationship(
        "Anomaly",
        back_populates="room",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="room",
    )
    patrol_stops: Mapped[List["PatrolStop"]] = relationship(
        "PatrolStop",
        back_populates="room",
    )


class RoomBaseline(Base):
    """Environmental thresholds and baseline expected values per room."""

    __tablename__ = "room_baselines"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique baseline record identifier",
    )
    room_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="Foreign key to target room",
    )
    gas_mq135_max: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        doc="Maximum safe MQ135 air quality reading threshold in ppm",
    )
    gas_mq2_max: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        doc="Maximum safe MQ2 combustible gas/smoke reading threshold in ppm",
    )
    motion_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="expect_motion",
        doc="Expected motion behavior: expect_motion, expect_no_motion, ignore",
    )
    no_motion_timeout_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=300,
        doc="Timeout in seconds without motion before raising anomaly in expect_motion mode",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Last threshold update timestamp in UTC",
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="baseline")

