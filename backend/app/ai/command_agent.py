"""Command parsing agent using direct Gemini SDK with structured output enforcement.

Per Section 2 of AGENTS.md:
- Direct Gemini SDK calls, NO LangChain/LangGraph.
- Schema conformance enforced via structured output / response_schema.
- Raises a clear exception on failure instead of returning invalid data.
"""

import json
from typing import Optional
import google.generativeai as genai
from pydantic import ValidationError

from app.ai.prompts import COMMAND_AGENT_SYSTEM_PROMPT
from app.core.config import settings
from app.schemas.commands import Command


class AICommandParsingError(Exception):
    """Raised when AI fails to parse text into a valid structured Command."""

    pass


def get_command_model(model_name: str = "gemini-1.5-flash") -> genai.GenerativeModel:
    """Instantiate and configure the Gemini model for structured Command parsing."""
    if not settings.GEMINI_API_KEY:
        raise AICommandParsingError("GEMINI_API_KEY is not configured in settings.")

    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=COMMAND_AGENT_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=Command,
            temperature=0.0,
        ),
    )


def parse_command_ai(
    text: str,
    model_name: str = "gemini-1.5-flash",
) -> Command:
    """Parse ambiguous natural language user input into a validated Command object.

    Args:
        text: Raw natural language command string.
        model_name: Gemini model name (defaults to gemini-1.5-flash).

    Returns:
        A validated Command instance.

    Raises:
        AICommandParsingError: If input is empty, API call fails, or output schema is invalid.
    """
    if not text or not isinstance(text, str) or not text.strip():
        raise AICommandParsingError("Cannot parse empty or invalid text input.")

    try:
        model = get_command_model(model_name=model_name)
        prompt = f"Parse the following user instruction into a Command object:\n\n{text.strip()}"
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise AICommandParsingError("Gemini returned an empty response.")

        return Command.model_validate_json(response.text)

    except AICommandParsingError:
        raise
    except (ValidationError, json.JSONDecodeError) as e:
        raise AICommandParsingError(
            f"Failed to validate Command JSON schema from AI output: {e}"
        ) from e
    except Exception as e:
        raise AICommandParsingError(
            f"Gemini API failure during command parsing: {e}"
        ) from e


async def parse_command_ai_async(
    text: str,
    model_name: str = "gemini-1.5-flash",
) -> Command:
    """Asynchronous variant of parse_command_ai.

    Args:
        text: Raw natural language command string.
        model_name: Gemini model name.

    Returns:
        A validated Command instance.

    Raises:
        AICommandParsingError: If input is empty, API call fails, or output schema is invalid.
    """
    if not text or not isinstance(text, str) or not text.strip():
        raise AICommandParsingError("Cannot parse empty or invalid text input.")

    try:
        model = get_command_model(model_name=model_name)
        prompt = f"Parse the following user instruction into a Command object:\n\n{text.strip()}"
        response = await model.generate_content_async(prompt)

        if not response or not response.text:
            raise AICommandParsingError("Gemini returned an empty async response.")

        return Command.model_validate_json(response.text)

    except AICommandParsingError:
        raise
    except (ValidationError, json.JSONDecodeError) as e:
        raise AICommandParsingError(
            f"Failed to validate Command JSON schema from AI async output: {e}"
        ) from e
    except Exception as e:
        raise AICommandParsingError(
            f"Gemini API async failure during command parsing: {e}"
        ) from e
