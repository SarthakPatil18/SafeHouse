"""State machine for robot device states, transitions, and priority command rules.

Per Section 4 and Section 6 of AGENTS.md:
- 11 Device States: IDLE, MOVING, TURNING, PATROLLING, SENSING, RECHECKING,
  RETURNING_HOME, OBSTACLE, LOW_BATTERY, ERROR, OFFLINE
- Priority stack: EMERGENCY_STOP > STOP > RETURN_HOME > RECHECK > PATROL > NORMAL_MOVEMENT
- Hard rejection rules:
  1. Reject START_PATROL if status == LOW_BATTERY or OFFLINE
  2. Reject any movement command if an unresolved OBSTACLE event is active
  3. STOP_ROVER / EMERGENCY_STOP always executes immediately, interrupting anything in progress
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.commands import Command, CommandIntent


class RobotState(str, Enum):
    """The 11 allowed robot device states defined in Section 6 of AGENTS.md."""

    IDLE = "IDLE"
    MOVING = "MOVING"
    TURNING = "TURNING"
    PATROLLING = "PATROLLING"
    SENSING = "SENSING"
    RECHECKING = "RECHECKING"
    RETURNING_HOME = "RETURNING_HOME"
    OBSTACLE = "OBSTACLE"
    LOW_BATTERY = "LOW_BATTERY"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class CommandRejectionError(Exception):
    """Raised when a command violates hard safety or priority rejection rules."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, current_state: RobotState, target_state: RobotState):
        message = f"Illegal state transition from {current_state.value} to {target_state.value}."
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


# Movement intents subject to obstacle and offline checks
MOVEMENT_INTENTS: Set[CommandIntent] = {
    CommandIntent.MOVE_FORWARD,
    CommandIntent.MOVE_BACKWARD,
    CommandIntent.TURN_LEFT,
    CommandIntent.TURN_RIGHT,
    CommandIntent.GO_TO_ROOM,
    CommandIntent.START_PATROL,
    CommandIntent.RETURN_HOME,
    CommandIntent.CHECK_ROOM,
}

# Legal state transition map
LEGAL_TRANSITIONS: Dict[RobotState, Set[RobotState]] = {
    RobotState.IDLE: {
        RobotState.IDLE,
        RobotState.MOVING,
        RobotState.TURNING,
        RobotState.PATROLLING,
        RobotState.SENSING,
        RobotState.RECHECKING,
        RobotState.RETURNING_HOME,
        RobotState.OBSTACLE,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.MOVING: {
        RobotState.IDLE,
        RobotState.MOVING,
        RobotState.TURNING,
        RobotState.SENSING,
        RobotState.OBSTACLE,
        RobotState.PATROLLING,
        RobotState.RETURNING_HOME,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.TURNING: {
        RobotState.IDLE,
        RobotState.MOVING,
        RobotState.TURNING,
        RobotState.SENSING,
        RobotState.OBSTACLE,
        RobotState.PATROLLING,
        RobotState.RETURNING_HOME,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.PATROLLING: {
        RobotState.IDLE,
        RobotState.MOVING,
        RobotState.TURNING,
        RobotState.PATROLLING,
        RobotState.SENSING,
        RobotState.RECHECKING,
        RobotState.RETURNING_HOME,
        RobotState.OBSTACLE,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.SENSING: {
        RobotState.IDLE,
        RobotState.PATROLLING,
        RobotState.RECHECKING,
        RobotState.MOVING,
        RobotState.RETURNING_HOME,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
        RobotState.OBSTACLE,
    },
    RobotState.RECHECKING: {
        RobotState.IDLE,
        RobotState.PATROLLING,
        RobotState.SENSING,
        RobotState.RETURNING_HOME,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
        RobotState.OBSTACLE,
    },
    RobotState.RETURNING_HOME: {
        RobotState.IDLE,
        RobotState.MOVING,
        RobotState.TURNING,
        RobotState.RETURNING_HOME,
        RobotState.OBSTACLE,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.OBSTACLE: {
        RobotState.IDLE,
        RobotState.RETURNING_HOME,
        RobotState.LOW_BATTERY,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.LOW_BATTERY: {
        RobotState.IDLE,
        RobotState.RETURNING_HOME,
        RobotState.ERROR,
        RobotState.OFFLINE,
    },
    RobotState.ERROR: {
        RobotState.IDLE,
        RobotState.LOW_BATTERY,
        RobotState.OFFLINE,
    },
    RobotState.OFFLINE: {
        RobotState.IDLE,
        RobotState.ERROR,
    },
}


class RobotStateMachine:
    """Manages robot device state, validates legal transitions, and enforces command rules."""

    def __init__(
        self,
        initial_state: RobotState = RobotState.IDLE,
        battery_level: float = 100.0,
        has_obstacle: bool = False,
    ):
        self.state: RobotState = initial_state
        self.battery_level: float = battery_level
        self.has_obstacle: bool = has_obstacle
        self.current_room_id: Optional[str] = None
        self.history: List[Tuple[RobotState, datetime]] = [
            (initial_state, datetime.now(timezone.utc))
        ]

    def transition_to(self, target_state: RobotState) -> RobotState:
        """Attempt to transition to a new device state.

        Args:
            target_state: Destination state.

        Returns:
            The updated RobotState.

        Raises:
            InvalidStateTransitionError: If the transition is illegal.
        """
        if self.state == target_state:
            return self.state

        if target_state not in LEGAL_TRANSITIONS.get(self.state, set()):
            raise InvalidStateTransitionError(self.state, target_state)

        self.state = target_state
        self.history.append((target_state, datetime.now(timezone.utc)))
        return self.state

    def trigger_obstacle(self) -> RobotState:
        """Trigger an active obstacle event and transition to OBSTACLE state."""
        self.has_obstacle = True
        if self.state not in (RobotState.OFFLINE, RobotState.ERROR):
            self.transition_to(RobotState.OBSTACLE)
        return self.state

    def resolve_obstacle(self) -> RobotState:
        """Resolve active obstacle and restore to IDLE if previously blocked."""
        self.has_obstacle = False
        if self.state == RobotState.OBSTACLE:
            self.transition_to(RobotState.IDLE)
        return self.state

    def set_battery_level(self, level: float) -> RobotState:
        """Update battery level and trigger LOW_BATTERY state if under threshold."""
        self.battery_level = max(0.0, min(100.0, level))
        if self.battery_level <= 15.0 and self.state not in (RobotState.OFFLINE, RobotState.ERROR):
            self.transition_to(RobotState.LOW_BATTERY)
        return self.state

    def set_offline(self) -> RobotState:
        """Mark device as offline."""
        return self.transition_to(RobotState.OFFLINE)

    def set_online(self) -> RobotState:
        """Bring device back online to IDLE."""
        if self.state == RobotState.OFFLINE:
            return self.transition_to(RobotState.IDLE)
        return self.state

    def validate_command(self, command: Command) -> None:
        """Enforce Section 4 hard rejection rules and state preconditions.

        Args:
            command: Command object to validate against current device state.

        Raises:
            CommandRejectionError: If the command violates priority or rejection rules.
        """
        intent = command.intent

        # 1. Immediate interrupt: STOP_ROVER / EMERGENCY_STOP always allowed
        if intent == CommandIntent.STOP_ROVER:
            return

        # 2. Rejection Rule: Disallow commands when device is OFFLINE
        if self.state == RobotState.OFFLINE:
            raise CommandRejectionError(
                code="ROBOT_OFFLINE",
                message=f"Cannot execute {intent.value}: Robot is currently OFFLINE.",
            )

        # 3. Hard Rejection Rule 1: Reject START_PATROL if LOW_BATTERY or OFFLINE
        if intent == CommandIntent.START_PATROL:
            if self.state == RobotState.LOW_BATTERY or self.battery_level <= 15.0:
                raise CommandRejectionError(
                    code="LOW_BATTERY",
                    message="Cannot start patrol: Device status is LOW_BATTERY.",
                )

        # 4. Hard Rejection Rule 2: Reject any movement command if unresolved OBSTACLE is active
        if intent in MOVEMENT_INTENTS and (self.has_obstacle or self.state == RobotState.OBSTACLE):
            raise CommandRejectionError(
                code="OBSTACLE_ACTIVE",
                message=f"Cannot execute {intent.value}: Unresolved obstacle event is active.",
            )

        # 5. Check if in ERROR state (only STOP or maintenance allowed)
        if self.state == RobotState.ERROR and intent in MOVEMENT_INTENTS:
            raise CommandRejectionError(
                code="ROBOT_ERROR",
                message=f"Cannot execute {intent.value}: Device is in an ERROR state.",
            )

        # 6. Check LOW_BATTERY restrictions on other movement (only RETURN_HOME permitted)
        if self.state == RobotState.LOW_BATTERY and intent in MOVEMENT_INTENTS and intent != CommandIntent.RETURN_HOME:
            raise CommandRejectionError(
                code="LOW_BATTERY",
                message=f"Cannot execute {intent.value}: Low battery mode permits only RETURN_HOME.",
            )

    def execute_command(self, command: Command) -> RobotState:
        """Validate and apply state transition for a validated command.

        Args:
            command: Command object to execute.

        Returns:
            The resulting RobotState after command execution.

        Raises:
            CommandRejectionError: If rejected by hard rules.
            InvalidStateTransitionError: If transition is illegal.
        """
        self.validate_command(command)
        intent = command.intent

        # Highest priority interrupt: STOP_ROVER / EMERGENCY_STOP
        if intent == CommandIntent.STOP_ROVER:
            if self.state != RobotState.OFFLINE:
                self.transition_to(RobotState.IDLE)
            return self.state

        # Patrol commands
        if intent == CommandIntent.START_PATROL:
            return self.transition_to(RobotState.PATROLLING)

        if intent == CommandIntent.STOP_PATROL:
            return self.transition_to(RobotState.IDLE)

        # Return home
        if intent == CommandIntent.RETURN_HOME:
            return self.transition_to(RobotState.RETURNING_HOME)

        # Manual movement
        if intent in (CommandIntent.MOVE_FORWARD, CommandIntent.MOVE_BACKWARD, CommandIntent.GO_TO_ROOM):
            if command.room_id:
                self.current_room_id = command.room_id
            return self.transition_to(RobotState.MOVING)

        if intent in (CommandIntent.TURN_LEFT, CommandIntent.TURN_RIGHT):
            return self.transition_to(RobotState.TURNING)

        # Recheck / inspect
        if intent == CommandIntent.CHECK_ROOM:
            if command.room_id:
                self.current_room_id = command.room_id
            return self.transition_to(RobotState.RECHECKING)

        # Read-only query commands do not alter state
        return self.state
