"""Command router coordinating deterministic rule-based parsing and AI escalation.

Per Section 2 of AGENTS.md:
- Deterministic keyword/rule matcher is the PRIMARY path.
- Gemini is only called when the rule matcher cannot confidently classify the input.
- If Gemini fails/times out, log and return an ErrorResponse (code AI_UNAVAILABLE)
  rather than crashing or silently guessing.
"""

from typing import Union
from app.ai.command_agent import parse_command_ai, parse_command_ai_async
from app.ai.rule_parser import parse_command_rule_based
from app.core.logging import logger
from app.schemas.commands import Command
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse


def parse_command(text: str) -> Union[SuccessResponse[Command], ErrorResponse]:
    """Parse user command text with rule-based priority and AI fallback.

    1. Attempts deterministic rule-based matching.
    2. If unclassified, escalates to Gemini Command Agent.
    3. If AI fails, logs error and returns a graceful ErrorResponse(code='AI_UNAVAILABLE').

    Args:
        text: Raw natural language command or transcription.

    Returns:
        SuccessResponse containing the validated Command, or ErrorResponse if parsing failed.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_COMMAND",
                message="Command text cannot be empty.",
            )
        )

    # 1. Deterministic Rule Matching (Primary Fast Path)
    rule_cmd = parse_command_rule_based(text)
    if rule_cmd is not None:
        return SuccessResponse(data=rule_cmd)

    # 2. AI Parsing Escalation
    try:
        ai_cmd = parse_command_ai(text)
        return SuccessResponse(data=ai_cmd)
    except Exception as e:
        logger.error(
            "AI command parsing failed for input '%s': %s",
            text,
            e,
            exc_info=True,
        )
        return ErrorResponse(
            error=ErrorDetail(
                code="AI_UNAVAILABLE",
                message="Natural language command understanding is temporarily unavailable.",
            )
        )


async def parse_command_async(
    text: str,
) -> Union[SuccessResponse[Command], ErrorResponse]:
    """Asynchronous variant of parse_command."""
    if not text or not isinstance(text, str) or not text.strip():
        return ErrorResponse(
            error=ErrorDetail(
                code="INVALID_COMMAND",
                message="Command text cannot be empty.",
            )
        )

    # 1. Deterministic Rule Matching (Primary Fast Path)
    rule_cmd = parse_command_rule_based(text)
    if rule_cmd is not None:
        return SuccessResponse(data=rule_cmd)

    # 2. Async AI Parsing Escalation
    try:
        ai_cmd = await parse_command_ai_async(text)
        return SuccessResponse(data=ai_cmd)
    except Exception as e:
        logger.error(
            "AI async command parsing failed for input '%s': %s",
            text,
            e,
            exc_info=True,
        )
        return ErrorResponse(
            error=ErrorDetail(
                code="AI_UNAVAILABLE",
                message="Natural language command understanding is temporarily unavailable.",
            )
        )
