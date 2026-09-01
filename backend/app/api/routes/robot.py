"""Robot control and status API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.robotics.state_machine import CommandRejectionError, RobotState
from app.schemas.commands import Command, CommandIntent
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.robot_service import RobotService, get_state_machine

router = APIRouter(prefix="/robot", tags=["Robot"])


@router.get("/status", response_model=SuccessResponse[Dict[str, Any]])
async def get_robot_status(db: AsyncSession = Depends(get_db)):
    """Retrieve live robot device status and telemetry."""
    status = await RobotService.get_status(db=db)
    return SuccessResponse(data=status)


@router.post("/command")
async def execute_command(
    command: Command,
    db: AsyncSession = Depends(get_db),
):
    """Execute a structured command on the rover with priority & safety validation."""
    try:
        result = await RobotService.execute_command(command, db=db)
        return SuccessResponse(data=result)
    except CommandRejectionError as e:
        return ErrorResponse(
            error=ErrorDetail(code=e.code, message=e.message)
        )
    except Exception as e:
        return ErrorResponse(
            error=ErrorDetail(code="EXECUTION_ERROR", message=str(e))
        )


@router.post("/stop")
async def emergency_stop(db: AsyncSession = Depends(get_db)):
    """Emergency halt rover immediately from any state."""
    cmd = Command(intent=CommandIntent.STOP_ROVER, priority="high")
    result = await RobotService.execute_command(cmd, db=db)
    return SuccessResponse(data=result)


@router.post("/obstacle")
async def toggle_obstacle(
    active: bool,
    db: AsyncSession = Depends(get_db),
):
    """Simulate or set obstacle status."""
    sm = get_state_machine()
    if active:
        sm.trigger_obstacle()
    else:
        sm.resolve_obstacle()
    return SuccessResponse(
        data={
            "has_obstacle": sm.has_obstacle,
            "status": sm.state.value,
        }
    )


@router.get("/events", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_robot_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve logged robot operational and hardware events."""
    events = await RobotService.list_events(db=db, limit=limit)
    return SuccessResponse(data=events)
