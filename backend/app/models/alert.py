"""SQLAlchemy models for detected anomalies and user alerts."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.reading import SensorReading
    from app.models.room import Room


class Anomaly(Base):
    """Deterministic rule-engine detected sensor anomalies."""

    __tablename__ = "anomalies"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique anomaly record identifier",
    )
    room_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Room where anomaly was detected",
    )
    reading_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sensor_readings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated sensor reading triggering anomaly",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Anomaly category (e.g. temperature_high, temperature_low, sound_spike, humidity_spike)",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Severity level (e.g. low, medium, high, critical)",
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Actual measured anomalous value",
    )
    expected_min: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Expected minimum baseline threshold",
    )
    expected_max: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Expected maximum baseline threshold",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="detected",
        nullable=False,
        doc="Anomaly resolution status (e.g. detected, rechecking, confirmed, resolved)",
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="UTC timestamp when anomaly was detected",
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when anomaly was resolved or dismissed",
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="anomalies")
    reading: Mapped[Optional["SensorReading"]] = relationship(
        "SensorReading",
        back_populates="anomalies",
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="anomaly",
        cascade="all, delete-orphan",
    )


class Alert(Base):
    """Caregiver and dashboard notifications generated from confirmed anomalies."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique alert identifier",
    )
    anomaly_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("anomalies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated anomaly triggering this alert",
    )
    room_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Target room identifier",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Alert severity (e.g. info, warning, critical)",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Plain language AI-reasoned or templated alert message",
    )
    channel: Mapped[str] = mapped_column(
        String(50),
        default="dashboard",
        nullable=False,
        doc="Notification dispatch channel (e.g. dashboard, push, sound)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        doc="Alert status (e.g. active, acknowledged, resolved)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Alert creation timestamp in UTC",
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when staff/caregiver acknowledged alert",
    )

    # Relationships
    anomaly: Mapped[Optional["Anomaly"]] = relationship("Anomaly", back_populates="alerts")
    room: Mapped[Optional["Room"]] = relationship("Room", back_populates="alerts")
