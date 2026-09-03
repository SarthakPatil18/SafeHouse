"""Sensor telemetry ingestion, offline buffer sync, and historical querying API endpoints."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import validate_device_token
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
    authenticated: bool = Depends(validate_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Ingest new live sensor reading and deterministically evaluate room baselines for anomalies."""
    result = await SensorService.record_reading(reading, db=db)
    return SuccessResponse(data=result)


@router.post("/sync", response_model=SuccessResponse[Dict[str, Any]])
async def sync_offline_sensor_readings(
    readings: List[SensorReadingCreate],
    authenticated: bool = Depends(validate_device_token),
    db: AsyncSession = Depends(get_db),
):
    """Sync a batch of offline buffered sensor readings in chronological order.

    Per Section 5b:
    1. Sort readings chronologically.
    2. Ingest through exact same SensorService.record_reading & AnomalyWorker pipeline.
    3. Mark each persisted record with source='buffered'.
    4. Return count and persisted indices.
    """
    if not readings:
        return SuccessResponse(
            data={
                "synced_count": 0,
                "persisted_indices": [],
                "readings": [],
            }
        )

    def _extract_timestamp(r: SensorReadingCreate) -> datetime:
        if r.timestamp is not None:
            if isinstance(r.timestamp, datetime):
                return r.timestamp if r.timestamp.tzinfo else r.timestamp.replace(tzinfo=timezone.utc)
            try:
                return datetime.fromisoformat(str(r.timestamp).replace("Z", "+00:00"))
            except Exception:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)

    # Track original array indices to report which indices succeeded
    indexed = list(enumerate(readings))
    # Sort chronologically ascending by timestamp
    indexed.sort(key=lambda item: _extract_timestamp(item[1]))

    persisted_indices: List[int] = []
    processed_results: List[Dict[str, Any]] = []

    for orig_idx, reading_in in indexed:
        # Mark as offline buffered telemetry
        reading_in.source = "buffered"
        result = await SensorService.record_reading(reading_in, db=db, process_worker=True)
        persisted_indices.append(orig_idx)
        processed_results.append(result)

    return SuccessResponse(
        data={
            "synced_count": len(processed_results),
            "persisted_indices": persisted_indices,
            "readings": processed_results,
        }
    )
