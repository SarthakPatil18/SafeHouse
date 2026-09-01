"""Room management and baseline configuration API endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["Rooms"])


class BaselineUpdateRequest(BaseModel):
    """Payload for updating room environmental threshold bounds."""

    temperature_min: float = Field(..., description="Minimum safe temperature in Celsius")
    temperature_max: float = Field(..., description="Maximum safe temperature in Celsius")
    humidity_min: float = Field(..., description="Minimum safe humidity percentage")
    humidity_max: float = Field(..., description="Maximum safe humidity percentage")
    sound_threshold: float = Field(..., description="Maximum safe sound level in dB")


@router.get("", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    """List all registered room waypoints and their environmental baselines."""
    rooms = await RoomService.list_rooms(db=db)
    return SuccessResponse(data=rooms)


@router.get("/{room_id}")
async def get_room_details(room_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a single room."""
    room = await RoomService.get_room(room_id, db=db)
    if not room:
        return ErrorResponse(
            error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room '{room_id}' not found.")
        )
    return SuccessResponse(data=room)


@router.put("/{room_id}/baseline")
async def update_room_baseline(
    room_id: str,
    baseline: BaselineUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update environmental baseline thresholds for a specific room."""
    room = await RoomService.get_room(room_id, db=db)
    if not room:
        return ErrorResponse(
            error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room '{room_id}' not found.")
        )

    updated = await RoomService.update_baseline(
        room_id=room_id,
        baseline_data=baseline.model_dump(),
        db=db,
    )
    return SuccessResponse(data=updated)
