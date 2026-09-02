"""Integration and unit tests for FastAPI REST endpoints and Section 7 envelope conformance."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.robotics.state_machine import RobotState
from app.schemas.commands import Command, CommandIntent
from app.services.robot_service import get_state_machine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure state machine starts in online IDLE state for each REST API test."""
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    sm.has_obstacle = False
    sm.battery_level = 98.0
    sm.current_room_id = None
    yield
    sm.state = RobotState.IDLE
    sm.has_obstacle = False


def test_root_and_health_endpoints():
    """Verify health and root endpoints return valid Section 7 API envelopes with system metrics."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    root_data = res_root.json()
    assert root_data["success"] is True
    assert root_data["error"] is None
    assert "service" in root_data["data"]

    res_health = client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["success"] is True
    assert health_data["error"] is None
    assert "db_reachable" in health_data["data"]
    assert "device_connected_count" in health_data["data"]
    assert "uptime_seconds" in health_data["data"]
    assert isinstance(health_data["data"]["device_connected_count"], int)
    assert isinstance(health_data["data"]["uptime_seconds"], (int, float))


def test_global_exception_handlers_section_7_envelope():
    """Verify 404, 422 validation, and unhandled errors all return consistent Section 7 envelope."""
    # 1. 404 Not Found unrouted endpoint
    res_404 = client.get("/api/completely-nonexistent-endpoint-xyz-123")
    assert res_404.status_code == 404
    body_404 = res_404.json()
    assert body_404["success"] is False
    assert body_404["data"] is None
    assert body_404["error"]["code"] == "NOT_FOUND"
    assert "timestamp" in body_404

    # 2. 422 Request Validation Error (missing required fields)
    res_422 = client.post("/api/rooms", json={"x": 1.0})  # Missing required name, type
    assert res_422.status_code == 422
    body_422 = res_422.json()
    assert body_422["success"] is False
    assert body_422["data"] is None
    assert body_422["error"]["code"] == "VALIDATION_ERROR"
    assert "timestamp" in body_422



def test_robot_status_and_commands():
    """Verify robot status retrieval, command execution, and emergency stop."""
    # 1. Status
    res = client.get("/api/robot/status")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "status" in body["data"]
    assert "battery_level" in body["data"]

    # 2. Command execution
    res = client.post(
        "/api/robot/command",
        json={"intent": "MOVE_FORWARD", "priority": "normal", "confirmation_required": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["command"] == "MOVE_FORWARD"
    assert body["data"]["status"] == "MOVING"

    # 3. Emergency stop
    res = client.post("/api/robot/stop")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "IDLE"


def test_robot_obstacle_toggle_and_rejection():
    """Verify obstacle mode causes movement rejection in REST API."""
    # Enable obstacle
    res = client.post("/api/robot/obstacle?active=true")
    assert res.status_code == 200
    assert res.json()["data"]["has_obstacle"] is True

    # Attempt movement -> Should return ErrorResponse(OBSTACLE_ACTIVE)
    res = client.post(
        "/api/robot/command",
        json={"intent": "MOVE_FORWARD", "priority": "normal", "confirmation_required": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "OBSTACLE_ACTIVE"

    # Clear obstacle
    client.post("/api/robot/obstacle?active=false")


def test_rooms_api_and_baseline_crud():
    """Verify room listing, single room details, and baseline updating."""
    # 1. List rooms
    res = client.get("/api/rooms")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) >= 4

    # 2. Get single room with baseline
    res = client.get("/api/rooms/room_1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["id"] == "room_1"
    assert "baseline" in body["data"]

    # 3. Create/Update baseline with valid expect_presence
    update_payload = {
        "gas_mq135_max": 95.0,
        "gas_mq2_max": 110.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 1800,
    }
    res = client.put("/api/rooms/room_1/baseline", json=update_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["gas_mq135_max"] == 95.0
    assert body["data"]["motion_mode"] == "expect_presence"
    assert body["data"]["no_motion_timeout_seconds"] == 1800


def test_rooms_crud_lifecycle_and_validation():
    """Verify full CRUD lifecycle and baseline validation rules."""
    # 1. Create a new room
    room_payload = {
        "id": "room_test_5",
        "name": "Sunroom",
        "type": "patio",
        "x": 8.0,
        "y": 4.0,
        "order_index": 5,
        "enabled": True,
        "baseline": {
            "gas_mq135_max": 90.0,
            "gas_mq2_max": 90.0,
            "motion_mode": "expect_absence",
            "no_motion_timeout_seconds": None,
        },
    }
    res = client.post("/api/rooms", json=room_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["id"] == "room_test_5"
    assert body["data"]["name"] == "Sunroom"

    # 2. Update room metadata
    update_res = client.put(
        "/api/rooms/room_test_5",
        json={"name": "Enclosed Sunroom", "enabled": False},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Enclosed Sunroom"
    assert update_res.json()["data"]["enabled"] is False

    # 3. Update baseline to ignore mode
    bl_res = client.put(
        "/api/rooms/room_test_5/baseline",
        json={
            "gas_mq135_max": 120.0,
            "gas_mq2_max": 130.0,
            "motion_mode": "ignore",
            "no_motion_timeout_seconds": None,
        },
    )
    assert bl_res.status_code == 200
    assert bl_res.json()["data"]["motion_mode"] == "ignore"

    # 4. Validation failure: expect_presence without no_motion_timeout_seconds
    bad_bl_res = client.put(
        "/api/rooms/room_test_5/baseline",
        json={
            "gas_mq135_max": 100.0,
            "gas_mq2_max": 100.0,
            "motion_mode": "expect_presence",
            "no_motion_timeout_seconds": None,
        },
    )
    assert bad_bl_res.status_code == 422  # Pydantic validation error

    # 5. Validation failure: invalid motion_mode
    invalid_mode_res = client.put(
        "/api/rooms/room_test_5/baseline",
        json={
            "gas_mq135_max": 100.0,
            "gas_mq2_max": 100.0,
            "motion_mode": "random_mode_xyz",
            "no_motion_timeout_seconds": 300,
        },
    )
    assert invalid_mode_res.status_code == 422

    # 6. Delete room
    del_res = client.delete("/api/rooms/room_test_5")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 7. Get deleted room -> should return ROOM_NOT_FOUND error response
    get_res = client.get("/api/rooms/room_test_5")
    assert get_res.status_code == 200
    assert get_res.json()["success"] is False
    assert get_res.json()["error"]["code"] == "ROOM_NOT_FOUND"



def test_sensors_api():
    """Verify sensor ingestion with anomaly detection, latest reading, and history."""
    # 1. Ingest normal reading
    reading_payload = {
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 40.0,
        "gas_mq2": 25.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 95.0,
    }
    res = client.post("/api/sensors/readings", json=reading_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "id" in body["data"]

    # 2. Ingest anomalous reading (high MQ135 gas)
    gas_payload = {
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 160.0,  # above 95.0
        "gas_mq2": 30.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 94.0,
    }
    res = client.post("/api/sensors/readings", json=gas_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]["anomalies"]) >= 1

    # 3. Latest
    res = client.get("/api/sensors/latest")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 4. History
    res = client.get("/api/sensors/history?limit=10")
    assert res.status_code == 200
    assert res.json()["success"] is True



def test_patrols_api():
    """Verify patrol start, stop, and list endpoints."""
    # 1. Start patrol
    res = client.post("/api/patrols/start")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "RUNNING"
    assert len(body["data"]["stops"]) >= 4

    # 2. List patrols
    res = client.get("/api/patrols")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 3. Stop patrol
    res = client.post("/api/patrols/stop")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "CANCELLED"


def test_alerts_api():
    """Verify alerts listing with status/room filters and acknowledgement lifecycle."""
    # 1. List all alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1

    # 2. Filter alerts by status and room
    res_room = client.get("/api/alerts?room=room_3")
    assert res_room.status_code == 200
    assert len(res_room.json()["data"]) >= 1
    assert res_room.json()["data"][0]["room_id"] == "room_3"

    res_empty_room = client.get("/api/alerts?room=room_nonexistent")
    assert res_empty_room.status_code == 200
    assert len(res_empty_room.json()["data"]) == 0

    # 3. Acknowledge alert
    res_ack = client.post("/api/alerts/alert_demo_1/acknowledge")
    assert res_ack.status_code == 200
    body_ack = res_ack.json()
    assert body_ack["success"] is True
    assert body_ack["data"]["status"] == "acknowledged"
    assert body_ack["data"]["acknowledged_at"] is not None

    # 4. Filter by acknowledged status
    res_status = client.get("/api/alerts?status=acknowledged")
    assert res_status.status_code == 200
    assert any(a["id"] == "alert_demo_1" for a in res_status.json()["data"])

    # 5. Acknowledge non-existent alert
    res_404 = client.post("/api/alerts/non_existent_alert_id/acknowledge")
    assert res_404.status_code == 200
    assert res_404.json()["success"] is False
    assert res_404.json()["error"]["code"] == "ALERT_NOT_FOUND"



def test_ai_command_api_stop_rule_path():
    """Verify sending 'stop' uses the deterministic rule path and reaches RobotService."""
    sm = get_state_machine()
    sm.state = RobotState.MOVING

    res = client.post("/api/ai/command", json={"text": "stop rover now"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["intent"] == "STOP_ROVER"
    assert body["data"]["result"]["status"] == "IDLE"
    assert sm.state == RobotState.IDLE


def test_ai_command_api_ambiguous_phrase_mocked_ai():
    """Verify sending an ambiguous phrase with AI mocked reaches correct service execution."""
    mock_command = Command(
        intent=CommandIntent.CHECK_ROOM,
        room_id="room_4",
        priority="normal",
        confirmation_required=False,
    )

    with patch("app.ai.command_router.parse_command_ai_async", new=AsyncMock(return_value=mock_command)):
        res = client.post(
            "/api/ai/command",
            json={"text": "could you please inspect what's happening in the kitchen"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["intent"] == "CHECK_ROOM"
        assert body["data"]["result"]["room_id"] == "room_4"


def test_ai_command_api_ai_unavailable_error_response():
    """Verify that if AI parsing fails, a clean AI_UNAVAILABLE error response is returned, not a 500."""
    with patch("app.ai.command_router.parse_command_ai_async", side_effect=RuntimeError("Gemini API timeout")):
        res = client.post(
            "/api/ai/command",
            json={"text": "very strange and ambiguous phrasing that cannot be rule matched"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["code"] == "AI_UNAVAILABLE"


def test_ai_command_api_take_snapshot_unsupported():
    """Verify TAKE_SNAPSHOT returns an explicit error stating no camera hardware exists."""
    res = client.post("/api/ai/command", json={"text": "take a snapshot of the room"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NO_CAMERA_HARDWARE"


def test_ai_command_api_rejection_rules():
    """Verify that priority and safety rejection rules are enforced prior to execution."""
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    sm.set_battery_level(10.0)  # Low battery

    # START_PATROL should be rejected due to low battery
    res = client.post("/api/ai/command", json={"text": "start patrol"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "LOW_BATTERY"

    # Restore battery and test obstacle rejection
    sm.set_battery_level(95.0)
    sm.state = RobotState.IDLE
    sm.trigger_obstacle()

    res_move = client.post("/api/ai/command", json={"text": "move forward"})
    assert res_move.status_code == 200
    body_move = res_move.json()
    assert body_move["success"] is False
    assert body_move["error"]["code"] == "OBSTACLE_ACTIVE"

    # Clear obstacle
    sm.resolve_obstacle()



def test_analytics_api():
    """Verify /api/analytics/summary returns overview metrics."""
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "total_patrols" in body["data"]
    assert "total_sensor_readings" in body["data"]
