"""Patrol mission lifecycle and waypoint routing API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.robotics.state_machine import CommandRejectionError
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.patrol_service import PatrolService

router = APIRouter(prefix="/patrols", tags=["Patrols"])


@router.get("", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_patrols(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve historical and active patrol missions."""
    patrols = await PatrolService.list_patrols(limit=limit, db=db)
    return SuccessResponse(data=patrols)


@router.post("/start")
async def start_patrol(
    device_id: str = "rover_01",
    db: AsyncSession = Depends(get_db),
):
    """Initiate an autonomous patrol sequence across configured rooms."""
    try:
        result = await PatrolService.start_patrol(device_id=device_id, db=db)
        return SuccessResponse(data=result)
    except CommandRejectionError as e:
        return ErrorResponse(
            error=ErrorDetail(code=e.code, message=e.message)
        )
    except Exception as e:
        return ErrorResponse(
            error=ErrorDetail(code="PATROL_START_FAILED", message=str(e))
        )


@router.post("/stop")
async def stop_patrol(
    device_id: str = "rover_01",
    patrol_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Halt or conclude the current patrol mission."""
    result = await PatrolService.stop_patrol(device_id=device_id, patrol_id=patrol_id, db=db)
    return SuccessResponse(data=result)
