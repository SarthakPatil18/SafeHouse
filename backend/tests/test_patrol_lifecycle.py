"""Unit and integration tests for PatrolService lifecycle, room advancement, and command dispatching."""

from unittest.mock import patch
import pytest

from app.robotics.state_machine import CommandRejectionError, RobotState
from app.services.device_manager import get_device_manager
from app.services.patrol_service import (
    PatrolService,
    get_active_patrol,
    reset_patrol_state,
)
from app.services.robot_service import get_state_machine


@pytest.fixture(autouse=True)
def clean_patrol_env():
    """Reset patrol, device manager, and state machine before each test."""
    reset_patrol_state()
    get_device_manager().clear()
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    sm.battery_level = 95.0
    sm.has_obstacle = False
    sm.current_room_id = None
    yield
    reset_patrol_state()
    get_device_manager().clear()


@pytest.mark.anyio
async def test_full_patrol_lifecycle_through_rooms():
    """Verify full patrol cycle: start -> advance through 3 rooms -> complete and return home."""
    mock_rooms = [
        {"id": "room_1", "name": "Living Room", "order_index": 1, "enabled": True},
        {"id": "room_2", "name": "Bedroom", "order_index": 2, "enabled": True},
        {"id": "room_3", "name": "Kitchen", "order_index": 3, "enabled": True},
    ]

    with patch("app.services.room_service.RoomService.list_rooms", return_value=mock_rooms):
        # 1. Start Patrol
        patrol = await PatrolService.start_patrol(device_id="rover_01")
        assert patrol["status"] == "RUNNING"
        assert len(patrol["stops"]) == 3
        assert patrol["stops"][0]["room_id"] == "room_1"
        assert patrol["stops"][0]["status"] == "arrived"

        # Assert first GO_TO_ROOM command dispatched
        dispatched = get_device_manager().get_dispatched_commands("rover_01")
        assert len(dispatched) == 1
        assert dispatched[0]["intent"] == "GO_TO_ROOM"
        assert dispatched[0]["room_id"] == "room_1"

        sm = get_state_machine()
        assert sm.state == RobotState.PATROLLING

        # 2. Advance from room_1 to room_2
        adv_1 = await PatrolService.advance_patrol(device_id="rover_01", room_id="room_1")
        assert adv_1["action"] == "ADVANCED_TO_NEXT_ROOM"
        assert adv_1["next_room_id"] == "room_2"
        assert patrol["stops"][0]["status"] == "completed"
        assert patrol["stops"][0]["departed_at"] is not None
        assert patrol["stops"][1]["status"] == "arrived"

        dispatched = get_device_manager().get_dispatched_commands("rover_01")
        assert len(dispatched) == 2
        assert dispatched[1]["intent"] == "GO_TO_ROOM"
        assert dispatched[1]["room_id"] == "room_2"

        # 3. Advance from room_2 to room_3 (last stop)
        adv_2 = await PatrolService.advance_patrol(device_id="rover_01", room_id="room_2")
        assert adv_2["action"] == "ADVANCED_TO_NEXT_ROOM"
        assert adv_2["next_room_id"] == "room_3"
        assert patrol["stops"][1]["status"] == "completed"

        dispatched = get_device_manager().get_dispatched_commands("rover_01")
        assert len(dispatched) == 3
        assert dispatched[2]["intent"] == "GO_TO_ROOM"
        assert dispatched[2]["room_id"] == "room_3"

        # 4. Advance from room_3 (Final Stop -> Completes Patrol & Returns Home)
        adv_3 = await PatrolService.advance_patrol(device_id="rover_01", room_id="room_3")
        assert adv_3["action"] == "PATROL_COMPLETED_RETURN_HOME"
        assert adv_3["patrol"]["status"] == "COMPLETED"
        assert adv_3["patrol"]["completed_at"] is not None

        # Assert RETURN_HOME command dispatched and state machine updated
        dispatched = get_device_manager().get_dispatched_commands("rover_01")
        assert len(dispatched) == 4
        assert dispatched[3]["intent"] == "RETURN_HOME"
        assert sm.state == RobotState.RETURNING_HOME
        assert get_active_patrol("rover_01") is None


@pytest.mark.anyio
async def test_patrol_rejected_on_low_battery():
    """Verify Section 4 hard rejection: reject START_PATROL when LOW_BATTERY or battery <= 15%."""
    sm = get_state_machine()
    sm.set_battery_level(10.0)
    assert sm.state == RobotState.LOW_BATTERY

    with pytest.raises(CommandRejectionError) as exc_info:
        await PatrolService.start_patrol(device_id="rover_01")

    assert exc_info.value.code == "LOW_BATTERY"
    assert get_active_patrol("rover_01") is None


@pytest.mark.anyio
async def test_mid_patrol_stop_patrol_halts_rover():
    """Verify mid-patrol stop_patrol call marks patrol CANCELLED and issues STOP_ROVER immediately."""
    mock_rooms = [
        {"id": "room_1", "name": "Living Room", "order_index": 1, "enabled": True},
        {"id": "room_2", "name": "Bedroom", "order_index": 2, "enabled": True},
    ]

    with patch("app.services.room_service.RoomService.list_rooms", return_value=mock_rooms):
        # 1. Start patrol
        patrol = await PatrolService.start_patrol(device_id="rover_01")
        assert patrol["status"] == "RUNNING"
        sm = get_state_machine()
        assert sm.state == RobotState.PATROLLING

        # 2. Issue mid-patrol stop_patrol
        cancelled_patrol = await PatrolService.stop_patrol(device_id="rover_01")
        assert cancelled_patrol["status"] == "CANCELLED"
        assert cancelled_patrol["completed_at"] is not None

        # Assert STOP_ROVER dispatched immediately and robot returned to IDLE
        dispatched = get_device_manager().get_dispatched_commands("rover_01")
        assert dispatched[-1]["intent"] == "STOP_ROVER"
        assert dispatched[-1]["priority"] == "high"
        assert sm.state == RobotState.IDLE
        assert get_active_patrol("rover_01") is None
