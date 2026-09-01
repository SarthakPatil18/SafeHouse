"""SQLAlchemy model for logging AI inference interactions."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIInteraction(Base):
    """Audit log for user voice/text parsing and reasoning AI interactions.

    Note: Kept short-retention / debug-only in accordance with Section 5 of AGENTS.md.
    """

    __tablename__ = "ai_interactions"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique AI interaction log ID",
    )
    user_input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw user voice transcript or text query",
    )
    intent: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Extracted intent code if classified",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Gemini model identifier used for inference",
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="AI response latency in milliseconds",
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether AI inference completed successfully without error",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp of interaction in UTC",
    )
