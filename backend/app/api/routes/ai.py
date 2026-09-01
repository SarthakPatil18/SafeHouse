"""AI command routing and anomaly explanation API endpoints."""

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.command_router import parse_command_async
from app.ai.reasoning_agent import AIReasoningError, explain_anomaly_async
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse

router = APIRouter(prefix="/ai", tags=["AI"])


class NaturalLanguageCommandRequest(BaseModel):
    """Payload containing natural language or voice transcription."""

    text: str = Field(..., description="User voice or text command", min_length=1)


class ExplainAnomalyRequest(BaseModel):
    """Context payload for generating an anomaly plain-language summary."""

    room_name: str = Field(..., description="Room name or identifier")
    type: str = Field(..., description="Anomaly type code (e.g. TEMPERATURE_LOW)")
    value: float = Field(..., description="Recorded sensor value")
    expected_min: float | None = Field(default=None, description="Expected baseline minimum")
    expected_max: float | None = Field(default=None, description="Expected baseline maximum")
    severity: str = Field(..., description="Pre-calculated severity (LOW, MEDIUM, HIGH)")
    trend: str | None = Field(default=None, description="Recent telemetry trend notes")


@router.post("/command")
async def process_natural_language_command(request: NaturalLanguageCommandRequest):
    """Parse natural language command using rule matcher first, escalating to Gemini if needed."""
    result = await parse_command_async(request.text)
    return result


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
