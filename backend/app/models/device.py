"""SQLAlchemy models for devices and robot events."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.patrol import Patrol
    from app.models.reading import SensorReading


class Device(Base):
    """Represents a rover or sensory hardware device."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique device identifier (e.g., rover_01 or UUID)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Friendly display name of the device",
    )
    device_type: Mapped[str] = mapped_column(
        String(50),
        default="rover",
        nullable=False,
        doc="Type classification (e.g., rover, fixed_sensor)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="IDLE",
        nullable=False,
        doc="Current robot device state (e.g. IDLE, PATROLLING, OFFLINE)",
    )
    battery_level: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False,
        doc="Current battery level percentage (0-100)",
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last ping/heartbeat timestamp from device",
    )
    firmware_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Current firmware build version",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Registration timestamp in UTC",
    )

    # Relationships
    readings: Mapped[List["SensorReading"]] = relationship(
        "SensorReading",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    patrols: Mapped[List["Patrol"]] = relationship(
        "Patrol",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    events: Mapped[List["RobotEvent"]] = relationship(
        "RobotEvent",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class RobotEvent(Base):
    """Hardware and operational events logged by robot devices."""

    __tablename__ = "robot_events"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique robot event identifier",
    )
    device_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to reporting device",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Event type (CONNECTED, DISCONNECTED, OBSTACLE_DETECTED, etc.)",
    )
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Structured event metadata or telemetry payload",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp when event occurred",
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="events")
