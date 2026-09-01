"""Sensor telemetry ingestion and historical querying API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import SuccessResponse
from app.schemas.sensors import SensorReadingCreate
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("/latest", response_model=SuccessResponse[Optional[Dict[str, Any]]])
async def get_latest_sensor_reading(
    device_id: str = "rover_01",
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the latest environmental reading reported by a rover."""
    reading = await SensorService.get_latest_reading(device_id=device_id, db=db)
    return SuccessResponse(data=reading)


@router.get("/history", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_sensor_history(
    room_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Query historical telemetry readings with optional room filtering."""
    history = await SensorService.get_history(room_id=room_id, limit=limit, db=db)
    return SuccessResponse(data=history)


@router.post("/readings")
async def record_sensor_reading(
    reading: SensorReadingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Ingest new sensor reading and deterministically evaluate room baselines for anomalies."""
    result = await SensorService.record_reading(reading, db=db)
    return SuccessResponse(data=result)
