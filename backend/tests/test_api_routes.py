"""Integration and unit tests for FastAPI REST endpoints and Section 7 envelope conformance."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.robotics.state_machine import RobotState
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
    """Verify health and root endpoints return valid Section 7 API envelopes."""
    for path in ["/", "/health"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["error"] is None
        assert "timestamp" in data
        assert isinstance(data["data"], dict)


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


def test_rooms_api():
    """Verify room listing, single room details, and baseline updating."""
    # 1. List rooms
    res = client.get("/api/rooms")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) >= 4

    # 2. Get single room
    res = client.get("/api/rooms/room_1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["id"] == "room_1"
    assert "baseline" in body["data"]

    # 3. Update baseline
    update_payload = {
        "temperature_min": 17.5,
        "temperature_max": 25.0,
        "humidity_min": 38.0,
        "humidity_max": 62.0,
        "sound_threshold": 55.0,
    }
    res = client.put("/api/rooms/room_1/baseline", json=update_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["temperature_min"] == 17.5


def test_sensors_api():
    """Verify sensor ingestion with anomaly detection, latest reading, and history."""
    # 1. Ingest normal reading
    reading_payload = {
        "device_id": "rover_01",
        "room_id": "room_1",
        "temperature": 21.0,
        "humidity": 45.0,
        "sound_level": 32.0,
        "battery": 95.0,
    }
    res = client.post("/api/sensors/readings", json=reading_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "id" in body["data"]

    # 2. Ingest anomalous reading (cold temp)
    cold_payload = {
        "device_id": "rover_01",
        "room_id": "room_1",
        "temperature": 12.0,  # below 17.5
        "humidity": 45.0,
        "sound_level": 32.0,
        "battery": 94.0,
    }
    res = client.post("/api/sensors/readings", json=cold_payload)
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
    """Verify alerts listing and acknowledgement."""
    # 1. List alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1

    # 2. Acknowledge alert
    res = client.post("/api/alerts/alert_demo_1/acknowledge")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "acknowledged"


def test_ai_command_api():
    """Verify /api/ai/command natural language endpoint via rule match."""
    res = client.post("/api/ai/command", json={"text": "check room 4"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["intent"] == "CHECK_ROOM"
    assert body["data"]["room_id"] == "room_4"


def test_analytics_api():
    """Verify /api/analytics/summary returns overview metrics."""
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "total_patrols" in body["data"]
    assert "total_sensor_readings" in body["data"]
