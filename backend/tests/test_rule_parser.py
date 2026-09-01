"""Unit tests for deterministic keyword and regex rule parser."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ai.rule_parser import normalize_room_id, parse_command_rule_based
from app.schemas.commands import CommandIntent


def test_normalize_room_id():
    """Verify room ID normalization."""
    assert normalize_room_id("room 4") == "room_4"
    assert normalize_room_id("Room 12") == "room_12"
    assert normalize_room_id("the bedroom") == "bedroom"
    assert normalize_room_id("Living Room") == "living_room"
    assert normalize_room_id("kitchen") == "kitchen"


def test_stop_rover():
    """Verify STOP_ROVER intent parsing."""
    cmd = parse_command_rule_based("stop")
    assert cmd is not None
    assert cmd.intent == CommandIntent.STOP_ROVER

    cmd = parse_command_rule_based("stop rover!")
    assert cmd is not None
    assert cmd.intent == CommandIntent.STOP_ROVER

    cmd = parse_command_rule_based("emergency stop")
    assert cmd is not None
    assert cmd.intent == CommandIntent.STOP_ROVER
    assert cmd.priority == "high"

    cmd = parse_command_rule_based("halt.")
    assert cmd is not None
    assert cmd.intent == CommandIntent.STOP_ROVER


def test_return_home():
    """Verify RETURN_HOME intent parsing."""
    for phrase in ["return home", "go home", "come back", "back to base", "dock", "return to dock", "go to charger"]:
        cmd = parse_command_rule_based(phrase)
        assert cmd is not None, f"Failed for phrase: {phrase}"
        assert cmd.intent == CommandIntent.RETURN_HOME


def test_start_patrol():
    """Verify START_PATROL intent parsing."""
    for phrase in ["patrol", "patrol all rooms", "start patrol", "patrol the house", "begin patrol"]:
        cmd = parse_command_rule_based(phrase)
        assert cmd is not None, f"Failed for phrase: {phrase}"
        assert cmd.intent == CommandIntent.START_PATROL


def test_stop_patrol():
    """Verify STOP_PATROL intent parsing."""
    for phrase in ["stop patrol", "end patrol", "cancel patrol", "pause patrol"]:
        cmd = parse_command_rule_based(phrase)
        assert cmd is not None, f"Failed for phrase: {phrase}"
        assert cmd.intent == CommandIntent.STOP_PATROL


def test_go_to_room():
    """Verify GO_TO_ROOM intent and room_id extraction."""
    cmd = parse_command_rule_based("go to room 4")
    assert cmd is not None
    assert cmd.intent == CommandIntent.GO_TO_ROOM
    assert cmd.room_id == "room_4"

    cmd = parse_command_rule_based("drive to the kitchen")
    assert cmd is not None
    assert cmd.intent == CommandIntent.GO_TO_ROOM
    assert cmd.room_id == "kitchen"

    cmd = parse_command_rule_based("navigate to living room")
    assert cmd is not None
    assert cmd.intent == CommandIntent.GO_TO_ROOM
    assert cmd.room_id == "living_room"


def test_check_room():
    """Verify CHECK_ROOM intent and room_id extraction."""
    cmd = parse_command_rule_based("check room 4")
    assert cmd is not None
    assert cmd.intent == CommandIntent.CHECK_ROOM
    assert cmd.room_id == "room_4"

    cmd = parse_command_rule_based("check on the bedroom")
    assert cmd is not None
    assert cmd.intent == CommandIntent.CHECK_ROOM
    assert cmd.room_id == "bedroom"

    cmd = parse_command_rule_based("inspect living room")
    assert cmd is not None
    assert cmd.intent == CommandIntent.CHECK_ROOM
    assert cmd.room_id == "living_room"

    cmd = parse_command_rule_based("scan room 2")
    assert cmd is not None
    assert cmd.intent == CommandIntent.CHECK_ROOM
    assert cmd.room_id == "room_2"


def test_get_status():
    """Verify GET_STATUS intent parsing."""
    for phrase in ["status", "get status", "rover status", "device status", "system status"]:
        cmd = parse_command_rule_based(phrase)
        assert cmd is not None, f"Failed for phrase: {phrase}"
        assert cmd.intent == CommandIntent.GET_STATUS


def test_get_room_status():
    """Verify GET_ROOM_STATUS intent and room_id extraction."""
    cmd = parse_command_rule_based("status of room 4")
    assert cmd is not None
    assert cmd.intent == CommandIntent.GET_ROOM_STATUS
    assert cmd.room_id == "room_4"

    cmd = parse_command_rule_based("get status of the kitchen")
    assert cmd is not None
    assert cmd.intent == CommandIntent.GET_ROOM_STATUS
    assert cmd.room_id == "kitchen"


def test_movement_and_turn_intents():
    """Verify manual movement intents."""
    # MOVE_FORWARD
    cmd = parse_command_rule_based("move forward")
    assert cmd is not None and cmd.intent == CommandIntent.MOVE_FORWARD
    cmd = parse_command_rule_based("forward")
    assert cmd is not None and cmd.intent == CommandIntent.MOVE_FORWARD

    # MOVE_BACKWARD
    cmd = parse_command_rule_based("move backward")
    assert cmd is not None and cmd.intent == CommandIntent.MOVE_BACKWARD
    cmd = parse_command_rule_based("reverse")
    assert cmd is not None and cmd.intent == CommandIntent.MOVE_BACKWARD
    cmd = parse_command_rule_based("back up")
    assert cmd is not None and cmd.intent == CommandIntent.MOVE_BACKWARD

    # TURN_LEFT
    cmd = parse_command_rule_based("turn left")
    assert cmd is not None and cmd.intent == CommandIntent.TURN_LEFT
    cmd = parse_command_rule_based("rotate left")
    assert cmd is not None and cmd.intent == CommandIntent.TURN_LEFT

    # TURN_RIGHT
    cmd = parse_command_rule_based("turn right")
    assert cmd is not None and cmd.intent == CommandIntent.TURN_RIGHT
    cmd = parse_command_rule_based("rotate right")
    assert cmd is not None and cmd.intent == CommandIntent.TURN_RIGHT


def test_history_alerts_snapshot():
    """Verify GET_HISTORY, GET_ALERTS, and TAKE_SNAPSHOT intents."""
    # GET_HISTORY
    cmd = parse_command_rule_based("history")
    assert cmd is not None and cmd.intent == CommandIntent.GET_HISTORY
    cmd = parse_command_rule_based("get history")
    assert cmd is not None and cmd.intent == CommandIntent.GET_HISTORY

    # GET_ALERTS
    cmd = parse_command_rule_based("alerts")
    assert cmd is not None and cmd.intent == CommandIntent.GET_ALERTS
    cmd = parse_command_rule_based("show alerts")
    assert cmd is not None and cmd.intent == CommandIntent.GET_ALERTS

    # TAKE_SNAPSHOT
    cmd = parse_command_rule_based("take snapshot")
    assert cmd is not None and cmd.intent == CommandIntent.TAKE_SNAPSHOT
    cmd = parse_command_rule_based("snapshot")
    assert cmd is not None and cmd.intent == CommandIntent.TAKE_SNAPSHOT
    cmd = parse_command_rule_based("take picture")
    assert cmd is not None and cmd.intent == CommandIntent.TAKE_SNAPSHOT


def test_ambiguous_phrases_return_none():
    """Verify that ambiguous, complex, or natural language phrases return None (escalate to AI)."""
    ambiguous_inputs = [
        "I think grandma might be cold in the bedroom, can you see what's happening?",
        "Is everything okay in the nursery?",
        "Why did the rover stop moving earlier today?",
        "Can you check if someone left the stove on in the kitchen?",
        "Hello, how are you today?",
        "What is the weather outside?",
        "Find my keys in the hallway",
        "It seems very quiet in room 2, please check if baby is awake",
        "",
        "   ",
    ]

    for phrase in ambiguous_inputs:
        cmd = parse_command_rule_based(phrase)
        assert cmd is None, f"Expected None for ambiguous phrase '{phrase}', got {cmd}"


if __name__ == "__main__":
    test_normalize_room_id()
    test_stop_rover()
    test_return_home()
    test_start_patrol()
    test_stop_patrol()
    test_go_to_room()
    test_check_room()
    test_get_status()
    test_get_room_status()
    test_movement_and_turn_intents()
    test_history_alerts_snapshot()
    test_ambiguous_phrases_return_none()
    print("All 12 rule parser tests passed successfully!")
