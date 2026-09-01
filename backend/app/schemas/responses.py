"""Pydantic schemas for generic API response envelopes."""

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Structured error information.

    Attributes:
        code: Error code string (e.g., ROBOT_OFFLINE, OBSTACLE_BLOCKED).
        message: Human-readable error description.
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of the error")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response envelope for all endpoints."""

    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[DataT] = Field(
        default=None,
        description="Response payload on success, null on error",
    )
    error: Optional[ErrorDetail] = Field(
        default=None,
        description="Error detail object on failure, null on success",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the response",
    )

    model_config = {"arbitrary_types_allowed": True}


class SuccessResponse(APIResponse[DataT], Generic[DataT]):
    """Successful API response envelope."""

    success: bool = Field(default=True, description="Always true for successful responses")
    data: DataT = Field(..., description="Response payload")
    error: None = Field(default=None, description="Always null for successful responses")


class ErrorResponse(APIResponse[None]):
    """Error API response envelope."""

    success: bool = Field(default=False, description="Always false for error responses")
    data: None = Field(default=None, description="Always null for error responses")
    error: ErrorDetail = Field(..., description="Error detail object")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "data": None,
                "error": {
                    "code": "ROBOT_OFFLINE",
                    "message": "Device cannot be reached.",
                },
                "timestamp": "2026-09-01T20:00:00Z",
            }
        }
    }
