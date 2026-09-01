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
    temperature: float = Field(..., description="Ambient temperature reading in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage (0-100)")
    sound_level: float = Field(..., description="Sound level measurement (dB or normalized)")
    battery: float = Field(..., description="Battery level percentage (0-100)")


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
                "temperature": 21.5,
                "humidity": 45.0,
                "sound_level": 32.0,
                "battery": 88.5,
            }
        },
    }
