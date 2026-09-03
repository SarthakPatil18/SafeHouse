"""AI command routing and anomaly explanation API endpoints.

Per Section 2, 3, 4, 7, and 8 of AGENTS.md:
- POST /api/ai/command accepts {"text": "..."}
- Calls command_router.parse_command_async (deterministic rule matcher primary path, Gemini fallback)
- Enforces robot state machine priority and hard rejection rules before execution
- Routes to appropriate service:
  * GO_TO_ROOM, CHECK_ROOM, RETURN_HOME, STOP_ROVER, movement -> RobotService
  * START_PATROL, STOP_PATROL -> PatrolService
  * GET_STATUS, GET_ROOM_STATUS, GET_HISTORY, GET_ALERTS -> Read-only queries
  * TAKE_SNAPSHOT -> Explicit error response (no camera in MVP)
- Every response uses the Section 7 envelope.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.command_router import parse_command_async
from app.ai.reasoning_agent import AIReasoningError, explain_anomaly_async
from app.core.db import get_db
from app.core.logging import logger
from app.robotics.state_machine import CommandRejectionError
from app.schemas.commands import Command, CommandIntent
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.alert_service import AlertService
from app.services.patrol_service import PatrolService
from app.services.robot_service import RobotService, get_state_machine
from app.services.room_service import RoomService
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/ai", tags=["AI"])


class NaturalLanguageCommandRequest(BaseModel):
    """Payload containing natural language or voice transcription."""

    text: str = Field(..., description="User voice or text command", min_length=1)


class ExplainAnomalyRequest(BaseModel):
    """Context payload for generating an anomaly plain-language summary."""

    room_name: str = Field(..., description="Room name or identifier")
    type: str = Field(..., description="Anomaly type code (e.g. gas_mq135_high)")
    value: float = Field(..., description="Recorded sensor value")
    expected_min: Optional[float] = Field(default=None, description="Expected baseline minimum")
    expected_max: Optional[float] = Field(default=None, description="Expected baseline maximum")
    severity: str = Field(..., description="Pre-calculated severity (LOW, MEDIUM, HIGH)")
    trend: Optional[str] = Field(default=None, description="Recent telemetry trend notes")


@router.post("/command")
async def process_natural_language_command(
    request: NaturalLanguageCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse and execute a natural language voice/text command through the system."""
    # 1. Parse command (Deterministic rule matcher first -> Gemini escalation fallback)
    parse_result = await parse_command_async(request.text)
    if not parse_result.success:
        return parse_result

    cmd: Command = parse_result.data
    intent = cmd.intent
    sm = get_state_machine()

    # 2. Check Section 4 Rejection Preconditions
    read_only_intents = {
        CommandIntent.GET_STATUS,
        CommandIntent.GET_ROOM_STATUS,
        CommandIntent.GET_HISTORY,
        CommandIntent.GET_ALERTS,
        CommandIntent.TAKE_SNAPSHOT,
    }

    if intent not in read_only_intents:
        try:
            sm.validate_command(cmd)
        except CommandRejectionError as e:
            return ErrorResponse(
                error=ErrorDetail(code=e.code, message=e.message)
            )

    # 3. Route to Target Service
    try:
        # A. Patrol Commands
        if intent == CommandIntent.START_PATROL:
            res = await PatrolService.start_patrol(db=db)
            stops_cnt = len(res.get("stops", []))
            first_stop = res.get("stops", [{}])[0].get("room_id", "waypoint").replace("_", " ")
            return SuccessResponse(
                data={
                    "intent": intent.value,
                    "result": res,
                    "message": f"Autonomous patrol started across {stops_cnt} zones. Heading to {first_stop}.",
                }
            )

        elif intent == CommandIntent.STOP_PATROL:
            res = await PatrolService.stop_patrol(db=db)
            return SuccessResponse(
                data={
                    "intent": intent.value,
                    "result": res,
                    "message": "Patrol mission stopped. Rover halted.",
                }
            )

        # B. Movement / Rover Operations
        elif intent in {
            CommandIntent.STOP_ROVER,
            CommandIntent.GO_TO_ROOM,
            CommandIntent.CHECK_ROOM,
            CommandIntent.RETURN_HOME,
            CommandIntent.MOVE_FORWARD,
            CommandIntent.MOVE_BACKWARD,
            CommandIntent.TURN_LEFT,
            CommandIntent.TURN_RIGHT,
        }:
            res = await RobotService.execute_command(cmd, db=db)
            if intent == CommandIntent.STOP_ROVER:
                msg = "Emergency stop engaged. Rover halted immediately."
            elif intent == CommandIntent.RETURN_HOME:
                msg = "Returning to docking base."
            elif cmd.room_id:
                msg = f"Navigating to {cmd.room_id.replace('_', ' ')}."
            else:
                msg = f"Executed {intent.value.replace('_', ' ')}. Rover state: {res.get('status', 'IDLE')}."
            return SuccessResponse(data={"intent": intent.value, "result": res, "message": msg})

        # C. Read-Only Telemetry / Status Queries
        elif intent == CommandIntent.GET_STATUS:
            status_data = await RobotService.get_status(db=db)
            return SuccessResponse(data={"intent": intent.value, "status": status_data})

        elif intent == CommandIntent.GET_ROOM_STATUS:
            if cmd.room_id:
                room_data = await RoomService.get_room(cmd.room_id, db=db)
                if not room_data:
                    return ErrorResponse(
                        error=ErrorDetail(
                            code="ROOM_NOT_FOUND",
                            message=f"Room '{cmd.room_id}' not found.",
                        )
                    )
                recent_readings = await SensorService.get_history(room_id=cmd.room_id, limit=5, db=db)
                return SuccessResponse(
                    data={
                        "intent": intent.value,
                        "room": room_data,
                        "recent_readings": recent_readings,
                    }
                )
            else:
                rooms = await RoomService.list_rooms(db=db)
                return SuccessResponse(data={"intent": intent.value, "rooms": rooms})

        elif intent == CommandIntent.GET_HISTORY:
            history = await SensorService.get_history(room_id=cmd.room_id, limit=20, db=db)
            return SuccessResponse(data={"intent": intent.value, "history": history})

        elif intent == CommandIntent.GET_ALERTS:
            alerts = await AlertService.list_alerts(db=db)
            return SuccessResponse(data={"intent": intent.value, "alerts": alerts})

        # D. Hardware Unsupported Intents
        elif intent == CommandIntent.TAKE_SNAPSHOT:
            return ErrorResponse(
                error=ErrorDetail(
                    code="NO_CAMERA_HARDWARE",
                    message="Snapshot command not supported: Camera hardware is not installed in this build.",
                )
            )

        else:
            return ErrorResponse(
                error=ErrorDetail(
                    code="UNKNOWN_INTENT",
                    message=f"Unhandled command intent '{intent.value}'.",
                )
            )

    except CommandRejectionError as e:
        return ErrorResponse(error=ErrorDetail(code=e.code, message=e.message))
    except Exception as e:
        logger.error("Error executing command intent %s: %s", intent, e, exc_info=True)
        return ErrorResponse(
            error=ErrorDetail(
                code="COMMAND_EXECUTION_ERROR",
                message=f"Failed to execute command '{intent.value}': {str(e)}",
            )
        )


@router.post("/explain")
async def explain_confirmed_anomaly(request: ExplainAnomalyRequest):
    """Generate a 1-2 sentence plain-language explanation for an already-confirmed anomaly."""
    try:
        explanation = await explain_anomaly_async(request.model_dump())
        return SuccessResponse(
            data={
                "explanation": explanation,
                "room": request.room_name,
                "severity": request.severity,
            }
        )
    except AIReasoningError as e:
        return ErrorResponse(
            error=ErrorDetail(code="AI_EXPLANATION_FAILED", message=str(e))
        )
    except Exception as e:
        return ErrorResponse(
            error=ErrorDetail(code="AI_ERROR", message=str(e))
        )
