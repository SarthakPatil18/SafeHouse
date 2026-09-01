"""SQLAlchemy models for patrol missions and patrol stop waypoints."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.room import Room


class Patrol(Base):
    """Represents an autonomous or commanded patrol execution session."""

    __tablename__ = "patrols"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique patrol mission identifier",
    )
    device_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Rover device executing this patrol",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="in_progress",
        nullable=False,
        doc="Patrol status (in_progress, completed, cancelled, failed)",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Patrol start timestamp in UTC",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Patrol completion/termination timestamp in UTC",
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="patrols")
    stops: Mapped[List["PatrolStop"]] = relationship(
        "PatrolStop",
        back_populates="patrol",
        cascade="all, delete-orphan",
        order_by="PatrolStop.sequence",
    )


class PatrolStop(Base):
    """Represents a scheduled or visited room stop during a patrol."""

    __tablename__ = "patrol_stops"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique patrol stop record identifier",
    )
    patrol_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("patrols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated patrol mission",
    )
    room_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target room for this waypoint stop",
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Sequence order index of this stop in the patrol",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        doc="Stop status (pending, arrived, completed, skipped)",
    )
    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp rover reached this waypoint",
    )
    departed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp rover departed from this waypoint",
    )

    # Relationships
    patrol: Mapped["Patrol"] = relationship("Patrol", back_populates="stops")
    room: Mapped["Room"] = relationship("Room", back_populates="patrol_stops")
