"""Deterministic keyword and regex rule-based parser for user commands.

Per Section 2 of AGENTS.md:
- Deterministic matcher is the PRIMARY path for fast, zero-dependency command classification.
- Returns a structured Command object for clear, confident matches.
- Returns None for ambiguous, natural-language, or uncertain inputs to allow escalation to Gemini AI.
"""

import re
from typing import Optional

from app.schemas.commands import Command, CommandIntent

CONVERSATIONAL_STOPWORDS = {
    "please",
    "can",
    "could",
    "would",
    "you",
    "if",
    "is",
    "are",
    "was",
    "grandpa",
    "grandma",
    "baby",
    "someone",
    "anyone",
    "lights",
    "stove",
    "cold",
    "warm",
    "hot",
    "okay",
    "fine",
    "see",
    "tell",
    "what",
    "why",
    "how",
    "who",
    "there",
    "look",
    "make",
    "sure",
}


def is_valid_room_name(raw_room: str) -> bool:
    """Check if the extracted text looks like a valid, concise room name rather than conversational text."""
    if not raw_room:
        return False
    tokens = [t for t in re.split(r"[\s_]+", raw_room.strip().lower()) if t]
    if not tokens or len(tokens) > 3:
        return False
    for token in tokens:
        if token in CONVERSATIONAL_STOPWORDS:
            return False
    return True


def normalize_room_id(raw_room: str) -> str:
    """Normalize raw room string into canonical room ID format.

    Examples:
        'room 4' -> 'room_4'
        'the bedroom' -> 'bedroom'
        'living room' -> 'living_room'
    """
    cleaned = raw_room.strip().lower()
    # Strip leading 'the '
    cleaned = re.sub(r"^the\s+", "", cleaned)
    # Convert 'room 4' / 'room  4' to 'room_4'
    cleaned = re.sub(r"^room\s+(\d+)$", r"room_\1", cleaned)
    # Replace spaces with underscores
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned


def parse_command_rule_based(text: str) -> Optional[Command]:
    """Parse user command text deterministically using exact keywords and regular expressions.

    Args:
        text: Raw user voice transcription or text input.

    Returns:
        A validated Command object if a confident rule match is found; otherwise None.
    """
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip().lower().rstrip(".?!")
    if not cleaned:
        return None

    # 1. STOP_ROVER / EMERGENCY_STOP
    if re.match(r"^(stop|stop rover|emergency stop|halt|freeze|abort)$", cleaned):
        priority = "high" if "emergency" in cleaned else "normal"
        return Command(
            intent=CommandIntent.STOP_ROVER,
            priority=priority,
            confirmation_required=False,
        )

    # 2. RETURN_HOME
    if re.match(r"^(return home|go home|come back|back to base|return to dock|dock|go to charger)$", cleaned):
        return Command(
            intent=CommandIntent.RETURN_HOME,
            priority="normal",
            confirmation_required=False,
        )

    # 3. STOP_PATROL
    if re.match(r"^(stop patrol|end patrol|cancel patrol|pause patrol)$", cleaned):
        return Command(
            intent=CommandIntent.STOP_PATROL,
            priority="normal",
            confirmation_required=False,
        )

    # 4. START_PATROL
    if re.match(r"^(start patrol|begin patrol|patrol all rooms|patrol the house|start patrolling|patrol)$", cleaned):
        return Command(
            intent=CommandIntent.START_PATROL,
            priority="normal",
            confirmation_required=False,
        )

    # 5. GET_STATUS
    if re.match(r"^(status|get status|rover status|device status|system status)$", cleaned):
        return Command(
            intent=CommandIntent.GET_STATUS,
            priority="normal",
            confirmation_required=False,
        )

    # 6. GET_HISTORY
    if re.match(r"^(get history|show history|view history|history|show sensor history|reading history)$", cleaned):
        return Command(
            intent=CommandIntent.GET_HISTORY,
            priority="normal",
            confirmation_required=False,
        )

    # 7. GET_ALERTS
    if re.match(r"^(get alerts|show alerts|list alerts|view alerts|alerts|active alerts)$", cleaned):
        return Command(
            intent=CommandIntent.GET_ALERTS,
            priority="normal",
            confirmation_required=False,
        )

    # 8. TAKE_SNAPSHOT
    if re.match(r"^(take snapshot|snapshot|take photo|take picture|capture image)$", cleaned):
        return Command(
            intent=CommandIntent.TAKE_SNAPSHOT,
            priority="normal",
            confirmation_required=False,
        )

    # 9. MOVE_FORWARD
    if re.match(r"^(move forward|go forward|drive forward|step forward|forward)$", cleaned):
        return Command(
            intent=CommandIntent.MOVE_FORWARD,
            priority="normal",
            confirmation_required=False,
        )

    # 10. MOVE_BACKWARD
    if re.match(r"^(move backward|move back|drive backward|go backward|step backward|backward|back up|reverse)$", cleaned):
        return Command(
            intent=CommandIntent.MOVE_BACKWARD,
            priority="normal",
            confirmation_required=False,
        )

    # 11. TURN_LEFT
    if re.match(r"^(turn left|rotate left|spin left|left turn)$", cleaned):
        return Command(
            intent=CommandIntent.TURN_LEFT,
            priority="normal",
            confirmation_required=False,
        )

    # 12. TURN_RIGHT
    if re.match(r"^(turn right|rotate right|spin right|right turn)$", cleaned):
        return Command(
            intent=CommandIntent.TURN_RIGHT,
            priority="normal",
            confirmation_required=False,
        )

    # 13. GET_ROOM_STATUS
    m_room_status = re.match(r"^(?:get\s+)?status\s+(?:of|for|in)\s+(?:the\s+)?(?P<room>[a-zA-Z0-9_\s]+)$", cleaned)
    if m_room_status:
        raw_room = m_room_status.group("room").strip()
        if is_valid_room_name(raw_room):
            room_id = normalize_room_id(raw_room)
            if room_id:
                return Command(
                    intent=CommandIntent.GET_ROOM_STATUS,
                    room_id=room_id,
                    priority="normal",
                    confirmation_required=False,
                )

    # 14. GO_TO_ROOM
    m_goto = re.match(r"^(?:go to|drive to|navigate to|head over to|head to)\s+(?:the\s+)?(?P<room>[a-zA-Z0-9_\s]+)$", cleaned)
    if m_goto:
        raw_room = m_goto.group("room").strip()
        if raw_room not in ("home", "base", "dock", "charger") and is_valid_room_name(raw_room):
            room_id = normalize_room_id(raw_room)
            if room_id:
                return Command(
                    intent=CommandIntent.GO_TO_ROOM,
                    room_id=room_id,
                    priority="normal",
                    confirmation_required=False,
                )

    # 15. CHECK_ROOM
    m_check = re.match(r"^(?:check(?:\s+on|\s+out)?|inspect|scan)\s+(?:the\s+)?(?P<room>[a-zA-Z0-9_\s]+)$", cleaned)
    if m_check:
        raw_room = m_check.group("room").strip()
        if raw_room not in ("status", "alerts", "history") and is_valid_room_name(raw_room):
            room_id = normalize_room_id(raw_room)
            if room_id:
                return Command(
                    intent=CommandIntent.CHECK_ROOM,
                    room_id=room_id,
                    priority="normal",
                    confirmation_required=False,
                )

    # Could not confidently match any deterministic pattern -> escalate to AI
    return None
