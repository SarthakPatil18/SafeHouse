"""Pydantic schemas for robot commands and intents."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CommandIntent(str, Enum):
    """The 15 allowed command intents defined in Section 3 of AGENTS.md."""

    MOVE_FORWARD = "MOVE_FORWARD"
    MOVE_BACKWARD = "MOVE_BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    STOP_ROVER = "STOP_ROVER"
    GO_TO_ROOM = "GO_TO_ROOM"
    CHECK_ROOM = "CHECK_ROOM"
    START_PATROL = "START_PATROL"
    STOP_PATROL = "STOP_PATROL"
    RETURN_HOME = "RETURN_HOME"
    GET_STATUS = "GET_STATUS"
    GET_ROOM_STATUS = "GET_ROOM_STATUS"
    GET_HISTORY = "GET_HISTORY"
    GET_ALERTS = "GET_ALERTS"
    TAKE_SNAPSHOT = "TAKE_SNAPSHOT"


class Command(BaseModel):
    """Structured robot command schema.

    Attributes:
        intent: The targeted robot action or query from CommandIntent.
        room_id: Target room identifier if required by the intent (e.g., CHECK_ROOM, GO_TO_ROOM).
        priority: Command priority level (defaults to "normal").
        confirmation_required: Whether user confirmation is needed before execution.
    """

    intent: CommandIntent = Field(..., description="Target command intent")
    room_id: Optional[str] = Field(
        default=None,
        description="Target room identifier if applicable (e.g. room_4)",
    )
    priority: str = Field(
        default="normal",
        description="Command priority level (e.g. normal, high, emergency)",
    )
    confirmation_required: bool = Field(
        default=False,
        description="Flag indicating if explicit confirmation is required before execution",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "intent": "CHECK_ROOM",
                "room_id": "room_4",
                "priority": "normal",
                "confirmation_required": False,
            }
        }
    }
