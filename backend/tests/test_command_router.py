"""Unit tests for the Command Router (rule-first with AI fallback and graceful error handling)."""

import asyncio
from unittest.mock import MagicMock, patch
import pytest

from app.ai.command_agent import AICommandParsingError
from app.ai.command_router import parse_command, parse_command_async
from app.schemas.commands import Command, CommandIntent
from app.schemas.responses import ErrorResponse, SuccessResponse


def test_rule_based_path_works_without_calling_ai():
    """Verify that deterministic commands resolve via rule_parser without ever invoking AI."""
    with patch("app.ai.command_router.parse_command_ai") as mock_ai:
        # 1. Stop
        res = parse_command("stop")
        assert isinstance(res, SuccessResponse)
        assert res.success is True
        assert res.data.intent == CommandIntent.STOP_ROVER
        mock_ai.assert_not_called()

        # 2. Go to room
        res = parse_command("go to room 4")
        assert isinstance(res, SuccessResponse)
        assert res.data.intent == CommandIntent.GO_TO_ROOM
        assert res.data.room_id == "room_4"
        mock_ai.assert_not_called()

        # 3. Check room
        res = parse_command("check bedroom")
        assert isinstance(res, SuccessResponse)
        assert res.data.intent == CommandIntent.CHECK_ROOM
        assert res.data.room_id == "bedroom"
        mock_ai.assert_not_called()

        # 4. Patrol
        res = parse_command("patrol all rooms")
        assert isinstance(res, SuccessResponse)
        assert res.data.intent == CommandIntent.START_PATROL
        mock_ai.assert_not_called()

        # 5. Status
        res = parse_command("status")
        assert isinstance(res, SuccessResponse)
        assert res.data.intent == CommandIntent.GET_STATUS
        mock_ai.assert_not_called()


def test_ai_escalation_success_on_ambiguous_command():
    """Verify that unclassified/ambiguous phrases escalate to AI and succeed."""
    mock_cmd = Command(
        intent=CommandIntent.CHECK_ROOM,
        room_id="room_4",
        priority="normal",
        confirmation_required=False,
    )

    with patch("app.ai.command_router.parse_command_ai", return_value=mock_cmd) as mock_ai:
        res = parse_command("I think something might be off in room 4, can you inspect it?")
        assert isinstance(res, SuccessResponse)
        assert res.success is True
        assert res.data.intent == CommandIntent.CHECK_ROOM
        assert res.data.room_id == "room_4"
        mock_ai.assert_called_once()


def test_ai_failure_returns_graceful_ai_unavailable_error():
    """Verify that when AI raises an exception or times out, router returns ErrorResponse(AI_UNAVAILABLE)."""
    with patch(
        "app.ai.command_router.parse_command_ai",
        side_effect=AICommandParsingError("Gemini API connection timeout"),
    ) as mock_ai:
        res = parse_command("Can you see if anyone left the lights on in the kitchen?")
        assert isinstance(res, ErrorResponse)
        assert res.success is False
        assert res.data is None
        assert res.error.code == "AI_UNAVAILABLE"
        assert "temporarily unavailable" in res.error.message
        mock_ai.assert_called_once()


def test_empty_input_returns_invalid_command_error():
    """Verify empty or whitespace strings return an INVALID_COMMAND ErrorResponse."""
    with patch("app.ai.command_router.parse_command_ai") as mock_ai:
        res = parse_command("")
        assert isinstance(res, ErrorResponse)
        assert res.success is False
        assert res.error.code == "INVALID_COMMAND"
        mock_ai.assert_not_called()


def test_async_router_behavior():
    """Verify async command router paths for rule success, AI success, and AI failure."""
    async def _run_async_tests():
        # 1. Rule match async
        with patch("app.ai.command_router.parse_command_ai_async") as mock_ai_async:
            res = await parse_command_async("return home")
            assert isinstance(res, SuccessResponse)
            assert res.data.intent == CommandIntent.RETURN_HOME
            mock_ai_async.assert_not_called()

        # 2. AI failure async
        with patch(
            "app.ai.command_router.parse_command_ai_async",
            side_effect=Exception("Network error"),
        ) as mock_ai_async:
            res = await parse_command_async("Check on grandpa in the bedroom please")
            assert isinstance(res, ErrorResponse)
            assert res.error.code == "AI_UNAVAILABLE"
            mock_ai_async.assert_called_once()

    asyncio.run(_run_async_tests())
