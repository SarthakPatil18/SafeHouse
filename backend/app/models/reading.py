"""SQLAlchemy model for recorded sensor readings."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.alert import Anomaly
    from app.models.device import Device
    from app.models.room import Room


class SensorReading(Base):
    """Environmental telemetry captured by rover/device sensors."""

    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique sensor reading identifier",
    )
    device_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to reporting rover/device",
    )
    room_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to room where reading was taken",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Timestamp when reading occurred in UTC",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Temperature in Celsius",
    )
    humidity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Relative humidity percentage",
    )
    sound_level: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Sound level measurement",
    )
    battery: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Device battery level percentage at time of reading",
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="readings")
    room: Mapped[Optional["Room"]] = relationship("Room", back_populates="readings")
    anomalies: Mapped[List["Anomaly"]] = relationship(
        "Anomaly",
        back_populates="reading",
    )
