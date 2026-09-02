"""Room management and baseline configuration API endpoints.

Per Section 5, 5a, and 7 of AGENTS.md:
- Full CRUD for rooms and room_baselines.
- Explicit baseline configuration (no auto-learning).
- Section 7 API envelope conformance for all responses.
- Validation:
  - motion_mode must be one of: expect_presence, expect_absence, ignore.
  - no_motion_timeout_seconds is required only when motion_mode is expect_presence.
"""

import enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["Rooms"])


class MotionModeEnum(str, enum.Enum):
    """Supported motion evaluation modes."""

    EXPECT_PRESENCE = "expect_presence"
    EXPECT_ABSENCE = "expect_absence"
    IGNORE = "ignore"


class BaselineUpdateRequest(BaseModel):
    """Payload for creating or updating room environmental baseline thresholds."""

    gas_mq135_max: float = Field(
        ..., gt=0, description="Maximum safe MQ135 air quality threshold in ppm"
    )
    gas_mq2_max: float = Field(
        ..., gt=0, description="Maximum safe MQ2 combustible gas threshold in ppm"
    )
    motion_mode: MotionModeEnum = Field(
        ..., description="Motion expectation: expect_presence, expect_absence, ignore"
    )
    no_motion_timeout_seconds: Optional[int] = Field(
        default=None,
        gt=0,
        description="No motion timeout in seconds (required only when motion_mode is expect_presence)",
    )

    @model_validator(mode="after")
    def validate_motion_timeout(self) -> "BaselineUpdateRequest":
        """Enforce that timeout is provided when motion is expected, and cleared otherwise."""
        mode_val = (
            self.motion_mode.value
            if isinstance(self.motion_mode, MotionModeEnum)
            else str(self.motion_mode)
        )
        if mode_val in ("expect_presence", "expect_motion"):
            if self.no_motion_timeout_seconds is None or self.no_motion_timeout_seconds <= 0:
                raise ValueError(
                    "no_motion_timeout_seconds is required and must be > 0 when motion_mode is 'expect_presence'"
                )
        else:
            self.no_motion_timeout_seconds = None
        return self


class RoomCreateRequest(BaseModel):
    """Payload for creating a new room waypoint."""

    id: Optional[str] = Field(None, description="Optional room ID (e.g. room_5)")
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable room name")
    type: str = Field(..., min_length=1, max_length=50, description="Room category (e.g. bedroom, kitchen)")
    x: float = Field(default=0.0, description="Spatial X coordinate")
    y: float = Field(default=0.0, description="Spatial Y coordinate")
    order_index: Optional[int] = Field(default=None, description="Patrol visitation order index")
    enabled: bool = Field(default=True, description="Whether room is included in active patrol")
    baseline: Optional[BaselineUpdateRequest] = Field(default=None, description="Initial room baseline")


class RoomUpdateRequest(BaseModel):
    """Payload for updating room waypoint metadata."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, min_length=1, max_length=50)
    x: Optional[float] = None
    y: Optional[float] = None
    order_index: Optional[int] = None
    enabled: Optional[bool] = None


@router.get("", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    """List all registered room waypoints and their current environmental baselines."""
    rooms = await RoomService.list_rooms(db=db)
    return SuccessResponse(data=rooms)


@router.get("/{room_id}")
async def get_room_details(room_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a single room with its current baseline."""
    room = await RoomService.get_room(room_id, db=db)
    if not room:
        return ErrorResponse(
            error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room '{room_id}' not found.")
        )
    return SuccessResponse(data=room)


@router.post("", response_model=SuccessResponse[Dict[str, Any]])
async def create_room(request: RoomCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new room waypoint and optional initial baseline."""
    created = await RoomService.create_room(
        room_data=request.model_dump(exclude_unset=True),
        db=db,
    )
    return SuccessResponse(data=created)


@router.put("/{room_id}")
async def update_room(
    room_id: str,
    request: RoomUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update room waypoint metadata."""
    room = await RoomService.get_room(room_id, db=db)
    if not room:
        return ErrorResponse(
            error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room '{room_id}' not found.")
        )

    updated = await RoomService.update_room(
        room_id=room_id,
        update_data=request.model_dump(exclude_unset=True),
        db=db,
    )
    return SuccessResponse(data=updated)


@router.delete("/{room_id}")
async def delete_room(room_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a room and its associated baseline configuration."""
    room = await RoomService.get_room(room_id, db=db)
    if not room:
        return ErrorResponse(
            error=ErrorDetail(code="ROOM_NOT_FOUND", message=f"Room '{room_id}' not found.")
        )

    deleted = await RoomService.delete_room(room_id, db=db)
    return SuccessResponse(data={"deleted": deleted, "room_id": room_id})


@router.put("/{room_id}/baseline")
@router.post("/{room_id}/baseline")
async def update_room_baseline(
    room_id: str,
    baseline: BaselineUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Explicitly set or update environmental baseline thresholds for a specific room."""
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
