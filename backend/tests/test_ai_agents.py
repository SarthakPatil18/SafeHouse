"""Unit tests for AI Command Agent and Reasoning Agent (using mocked Gemini responses)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.ai.command_agent import (
    AICommandParsingError,
    parse_command_ai,
)
from app.ai.prompts import (
    COMMAND_AGENT_SYSTEM_PROMPT,
    REASONING_AGENT_SYSTEM_PROMPT,
)
from app.ai.reasoning_agent import (
    AIReasoningError,
    explain_anomaly,
)
from app.schemas.commands import CommandIntent


def test_prompts_content():
    """Verify prompt constraints."""
    # Command Agent prompt must contain all 15 intents
    for intent in CommandIntent:
        assert intent.value in COMMAND_AGENT_SYSTEM_PROMPT

    # Reasoning Agent prompt must explicitly forbid deciding severity
    assert "DO NOT decide, calculate, or alter the severity" in REASONING_AGENT_SYSTEM_PROMPT
    assert "DO NOT decide or evaluate whether an anomaly exists" in REASONING_AGENT_SYSTEM_PROMPT


def test_parse_command_ai_success():
    """Verify parse_command_ai parses valid Gemini JSON output into a Command."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "intent": "CHECK_ROOM",
        "room_id": "room_4",
        "priority": "normal",
        "confirmation_required": False,
    })

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("app.ai.command_agent.get_command_model", return_value=mock_model):
        cmd = parse_command_ai("Could you go take a look at room 4?")
        assert cmd.intent == CommandIntent.CHECK_ROOM
        assert cmd.room_id == "room_4"
        assert cmd.priority == "normal"
        assert cmd.confirmation_required is False


def test_parse_command_ai_invalid_json_raises_error():
    """Verify parse_command_ai raises AICommandParsingError on malformed JSON."""
    mock_response = MagicMock()
    mock_response.text = "This is not JSON"

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("app.ai.command_agent.get_command_model", return_value=mock_model):
        with pytest.raises(AICommandParsingError) as exc_info:
            parse_command_ai("Check the living room")
        assert "Failed to validate Command JSON schema" in str(exc_info.value)


def test_parse_command_ai_invalid_intent_raises_error():
    """Verify parse_command_ai raises AICommandParsingError on hallucinated/invalid intent."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "intent": "COOK_DINNER",  # Not in the 15 intents
        "room_id": "kitchen",
    })

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("app.ai.command_agent.get_command_model", return_value=mock_model):
        with pytest.raises(AICommandParsingError):
            parse_command_ai("Cook dinner in the kitchen")


def test_parse_command_ai_empty_text_raises_error():
    """Verify parse_command_ai raises error when empty input is passed."""
    with pytest.raises(AICommandParsingError):
        parse_command_ai("")


def test_explain_anomaly_success():
    """Verify explain_anomaly passes context to Gemini and returns explanation."""
    mock_response = MagicMock()
    mock_response.text = "Elevated hazardous gas detected in Bedroom 1 (160.0 ppm), exceeding the safe baseline of 80.0 ppm. Please verify ventilation."

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    context = {
        "room_name": "Bedroom 1",
        "type": "gas_mq135_high",
        "value": 160.0,
        "expected_min": None,
        "expected_max": 80.0,
        "severity": "HIGH",
        "trend": "Rising 20 ppm per 5 minutes",
    }

    with patch("app.ai.reasoning_agent.get_reasoning_model", return_value=mock_model):
        explanation = explain_anomaly(context)
        assert "hazardous gas" in explanation.lower() or "bedroom 1" in explanation.lower()
        mock_model.generate_content.assert_called_once()
        prompt_arg = mock_model.generate_content.call_args[0][0]
        # Verify pre-calculated severity was injected into prompt
        assert "HIGH" in prompt_arg
        assert "Bedroom 1" in prompt_arg



def test_explain_anomaly_empty_context_raises_error():
    """Verify explain_anomaly raises error on empty context."""
    with pytest.raises(AIReasoningError):
        explain_anomaly({})
