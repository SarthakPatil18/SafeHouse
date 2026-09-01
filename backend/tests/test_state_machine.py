"""Unit tests for Robot State Machine, legal transitions, priority stack, and rejection rules."""

import pytest

from app.robotics.state_machine import (
    CommandRejectionError,
    InvalidStateTransitionError,
    RobotState,
    RobotStateMachine,
)
from app.schemas.commands import Command, CommandIntent


def test_eleven_robot_states_defined():
    """Verify that all 11 states from AGENTS.md Section 6 are present."""
    expected_states = {
        "IDLE",
        "MOVING",
        "TURNING",
        "PATROLLING",
        "SENSING",
        "RECHECKING",
        "RETURNING_HOME",
        "OBSTACLE",
        "LOW_BATTERY",
        "ERROR",
        "OFFLINE",
    }
    actual_states = {s.value for s in RobotState}
    assert actual_states == expected_states
    assert len(RobotState) == 11


def test_rejected_patrol_start_on_low_battery():
    """Hard Rule 1: Reject START_PATROL if device status == LOW_BATTERY or battery <= 15%."""
    # 1. In LOW_BATTERY state
    sm = RobotStateMachine(initial_state=RobotState.LOW_BATTERY, battery_level=10.0)
    cmd = Command(intent=CommandIntent.START_PATROL)

    with pytest.raises(CommandRejectionError) as exc_info:
        sm.execute_command(cmd)
    assert exc_info.value.code == "LOW_BATTERY"
    assert "LOW_BATTERY" in exc_info.value.message

    # 2. Starting with 10% battery in IDLE triggers rejection
    sm2 = RobotStateMachine(initial_state=RobotState.IDLE, battery_level=12.0)
    with pytest.raises(CommandRejectionError) as exc_info:
        sm2.execute_command(cmd)
    assert exc_info.value.code == "LOW_BATTERY"


def test_rejected_patrol_start_on_offline():
    """Hard Rule 1: Reject START_PATROL if device status == OFFLINE."""
    sm = RobotStateMachine(initial_state=RobotState.OFFLINE)
    cmd = Command(intent=CommandIntent.START_PATROL)

    with pytest.raises(CommandRejectionError) as exc_info:
        sm.execute_command(cmd)
    assert exc_info.value.code == "ROBOT_OFFLINE"


def test_obstacle_blocking_movement_commands():
    """Hard Rule 2: Reject any movement command if an unresolved OBSTACLE event is active."""
    sm = RobotStateMachine(initial_state=RobotState.IDLE)
    sm.trigger_obstacle()
    assert sm.state == RobotState.OBSTACLE
    assert sm.has_obstacle is True

    # Test rejection across all movement intents
    movement_commands = [
        Command(intent=CommandIntent.MOVE_FORWARD),
        Command(intent=CommandIntent.MOVE_BACKWARD),
        Command(intent=CommandIntent.TURN_LEFT),
        Command(intent=CommandIntent.TURN_RIGHT),
        Command(intent=CommandIntent.GO_TO_ROOM, room_id="room_4"),
        Command(intent=CommandIntent.START_PATROL),
        Command(intent=CommandIntent.CHECK_ROOM, room_id="room_2"),
    ]

    for cmd in movement_commands:
        with pytest.raises(CommandRejectionError) as exc_info:
            sm.execute_command(cmd)
        assert exc_info.value.code == "OBSTACLE_ACTIVE"

    # Once resolved, movement should be permitted
    sm.resolve_obstacle()
    assert sm.state == RobotState.IDLE
    assert sm.has_obstacle is False

    new_state = sm.execute_command(Command(intent=CommandIntent.MOVE_FORWARD))
    assert new_state == RobotState.MOVING


def test_emergency_stop_interrupts_patrolling_state():
    """Hard Rule 3: STOP_ROVER / EMERGENCY_STOP always executes immediately from any state."""
    # 1. Interrupt PATROLLING
    sm = RobotStateMachine(initial_state=RobotState.PATROLLING)
    cmd = Command(intent=CommandIntent.STOP_ROVER, priority="high")
    result = sm.execute_command(cmd)
    assert result == RobotState.IDLE
    assert sm.state == RobotState.IDLE

    # 2. Interrupt MOVING
    sm.transition_to(RobotState.MOVING)
    result = sm.execute_command(Command(intent=CommandIntent.STOP_ROVER))
    assert result == RobotState.IDLE

    # 3. Interrupt RECHECKING
    sm.transition_to(RobotState.RECHECKING)
    result = sm.execute_command(Command(intent=CommandIntent.STOP_ROVER))
    assert result == RobotState.IDLE

    # 4. Interrupt OBSTACLE state
    sm.trigger_obstacle()
    result = sm.execute_command(Command(intent=CommandIntent.STOP_ROVER))
    assert result == RobotState.IDLE


def test_legal_patrol_lifecycle_transitions():
    """Verify full healthy patrol lifecycle state transitions."""
    sm = RobotStateMachine(initial_state=RobotState.IDLE)

    # 1. Start patrol -> PATROLLING
    sm.execute_command(Command(intent=CommandIntent.START_PATROL))
    assert sm.state == RobotState.PATROLLING

    # 2. Arrive in room for rechecking/sensing -> RECHECKING
    sm.transition_to(RobotState.RECHECKING)
    assert sm.state == RobotState.RECHECKING

    # 3. Resume patrol -> PATROLLING
    sm.transition_to(RobotState.PATROLLING)
    assert sm.state == RobotState.PATROLLING

    # 4. Finish and return home -> RETURNING_HOME
    sm.execute_command(Command(intent=CommandIntent.RETURN_HOME))
    assert sm.state == RobotState.RETURNING_HOME

    # 5. Docked at base -> IDLE
    sm.execute_command(Command(intent=CommandIntent.STOP_ROVER))
    assert sm.state == RobotState.IDLE


def test_illegal_state_transitions_raise_error():
    """Verify illegal state transitions raise InvalidStateTransitionError."""
    sm = RobotStateMachine(initial_state=RobotState.OFFLINE)

    # Cannot transition directly from OFFLINE to MOVING without first coming online (IDLE)
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(RobotState.MOVING)
