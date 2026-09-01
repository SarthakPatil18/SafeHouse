"""Reasoning agent for generating plain-language anomaly explanations.

Per Section 2 of AGENTS.md:
- Explains an ALREADY-CONFIRMED anomaly in plain language (1-2 sentences).
- AI NEVER decides severity and NEVER decides anomaly status (severity is passed in pre-computed).
- Direct Gemini SDK calls, NO LangChain/LangGraph.
"""

from typing import Any, Dict
import google.generativeai as genai

from app.ai.prompts import REASONING_AGENT_SYSTEM_PROMPT
from app.core.config import settings


class AIReasoningError(Exception):
    """Raised when AI fails to generate an anomaly explanation."""

    pass


def get_reasoning_model(model_name: str = "gemini-1.5-flash") -> genai.GenerativeModel:
    """Instantiate and configure the Gemini model for anomaly reasoning."""
    if not settings.GEMINI_API_KEY:
        raise AIReasoningError("GEMINI_API_KEY is not configured in settings.")

    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=REASONING_AGENT_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=150,
        ),
    )


def _build_explanation_prompt(context: Dict[str, Any]) -> str:
    """Format anomaly context into a structured prompt."""
    room = context.get("room_name") or context.get("room_id") or "Unknown Room"
    anomaly_type = context.get("type") or context.get("anomaly_type") or "Sensor Anomaly"
    value = context.get("value") or context.get("current_value")
    exp_min = context.get("expected_min") or context.get("baseline_min")
    exp_max = context.get("expected_max") or context.get("baseline_max")
    severity = context.get("severity", "MEDIUM")
    trend = context.get("trend")

    range_desc = ""
    if exp_min is not None and exp_max is not None:
        range_desc = f"expected range: {exp_min} to {exp_max}"
    elif exp_max is not None:
        range_desc = f"threshold ceiling: {exp_max}"
    elif exp_min is not None:
        range_desc = f"threshold floor: {exp_min}"

    prompt = f"""Explain this confirmed anomaly in 1 to 2 concise sentences for the caregiver dashboard:
- Room: {room}
- Anomaly Type: {anomaly_type}
- Recorded Value: {value}
- Baseline Safe Bounds: {range_desc}
- Pre-calculated Severity: {severity}
"""
    if trend:
        prompt += f"- Recent Telemetry Trend: {trend}\n"

    return prompt


def explain_anomaly(
    context: Dict[str, Any],
    model_name: str = "gemini-1.5-flash",
) -> str:
    """Generate a 1-2 sentence plain-language explanation for an already-confirmed anomaly.

    Args:
        context: Dictionary with anomaly metadata (room, type, value, baseline, severity, trend).
        model_name: Gemini model name.

    Returns:
        One or two natural language sentences explaining the event.

    Raises:
        AIReasoningError: If API call fails or response is empty.
    """
    if not context or not isinstance(context, dict):
        raise AIReasoningError("Anomaly context must be a non-empty dictionary.")

    try:
        model = get_reasoning_model(model_name=model_name)
        prompt = _build_explanation_prompt(context)
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise AIReasoningError("Gemini returned an empty explanation.")

        return response.text.strip()

    except AIReasoningError:
        raise
    except Exception as e:
        raise AIReasoningError(
            f"Gemini API failure during anomaly explanation: {e}"
        ) from e


async def explain_anomaly_async(
    context: Dict[str, Any],
    model_name: str = "gemini-1.5-flash",
) -> str:
    """Asynchronous variant of explain_anomaly.

    Args:
        context: Dictionary with anomaly metadata.
        model_name: Gemini model name.

    Returns:
        One or two natural language sentences explaining the event.

    Raises:
        AIReasoningError: If API call fails or response is empty.
    """
    if not context or not isinstance(context, dict):
        raise AIReasoningError("Anomaly context must be a non-empty dictionary.")

    try:
        model = get_reasoning_model(model_name=model_name)
        prompt = _build_explanation_prompt(context)
        response = await model.generate_content_async(prompt)

        if not response or not response.text:
            raise AIReasoningError("Gemini returned an empty async explanation.")

        return response.text.strip()

    except AIReasoningError:
        raise
    except Exception as e:
        raise AIReasoningError(
            f"Gemini API async failure during anomaly explanation: {e}"
        ) from e
