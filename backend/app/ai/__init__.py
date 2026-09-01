"""AI package initialization."""

from app.ai.command_agent import (
    AICommandParsingError,
    parse_command_ai,
    parse_command_ai_async,
)
from app.ai.command_router import parse_command, parse_command_async
from app.ai.prompts import (
    COMMAND_AGENT_SYSTEM_PROMPT,
    REASONING_AGENT_SYSTEM_PROMPT,
)
from app.ai.reasoning_agent import (
    AIReasoningError,
    explain_anomaly,
    explain_anomaly_async,
)
from app.ai.rule_parser import normalize_room_id, parse_command_rule_based

__all__ = [
    "COMMAND_AGENT_SYSTEM_PROMPT",
    "REASONING_AGENT_SYSTEM_PROMPT",
    "parse_command_rule_based",
    "normalize_room_id",
    "parse_command_ai",
    "parse_command_ai_async",
    "AICommandParsingError",
    "explain_anomaly",
    "explain_anomaly_async",
    "AIReasoningError",
    "parse_command",
    "parse_command_async",
]
