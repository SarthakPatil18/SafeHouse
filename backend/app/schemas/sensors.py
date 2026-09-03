"""Pydantic schemas for sensor readings matching the sensor_readings data model."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class SensorReadingBase(BaseModel):
    """Base schema for sensor readings captured by device sensors."""

    device_id: str = Field(..., description="Unique identifier of the reporting device")
    room_id: Optional[str] = Field(
        default=None,
        description="Room identifier where the sensor reading was captured",
    )
    pir_motion: bool = Field(
        default=False,
        description="PIR motion detection status (true if motion detected)",
    )
    gas_mq135: float = Field(
        ...,
        description="MQ135 air quality / hazardous gas reading in ppm",
    )
    gas_mq2: float = Field(
        ...,
        description="MQ2 combustible gas and smoke reading in ppm",
    )
    ultrasonic_distance_cm: float = Field(
        ...,
        description="Ultrasonic obstacle distance measurement in cm",
    )
    battery: float = Field(
        ...,
        description="Battery level percentage (0-100)",
    )
    no_motion_seconds: Optional[float] = Field(
        default=None,
        description="Elapsed seconds without motion (optional for simulation telemetry)",
    )
    source: str = Field(
        default="live",
        description="Ingest source: 'live' or 'buffered'",
    )

    model_config = {"extra": "allow"}



class SensorReadingCreate(SensorReadingBase):
    """Schema for incoming sensor readings sent by hardware or simulation."""

    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the reading occurred (UTC)",
    )


class SensorReading(SensorReadingBase):
    """Schema for persisted sensor readings retrieved from the database."""

    id: str = Field(..., description="Unique sensor reading identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the reading occurred (UTC)",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "sr_12345",
                "device_id": "rover_01",
                "room_id": "room_4",
                "timestamp": "2026-09-01T20:00:00Z",
                "pir_motion": False,
                "gas_mq135": 35.5,
                "gas_mq2": 22.0,
                "ultrasonic_distance_cm": 120.0,
                "battery": 88.5,
            }
        },
    }

