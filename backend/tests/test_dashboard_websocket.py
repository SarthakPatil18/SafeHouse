"""Unit and integration tests for browser-facing Dashboard WebSocket broadcasts."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.robotics.state_machine import RobotState
from app.services.dashboard_broadcaster import dashboard_manager
from app.services.robot_service import get_state_machine
from app.workers.anomaly_worker import reset_worker_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset connection manager and state before each test."""
    dashboard_manager.clear()
    reset_worker_state()
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    yield
    dashboard_manager.clear()
    reset_worker_state()


def test_two_dashboard_clients_receive_sensor_update_broadcast():
    """Verify that multiple connected browser dashboard clients receive live sensor updates."""
    with client.websocket_connect("/ws/dashboard") as client_1:
        with client.websocket_connect("/ws/dashboard") as client_2:
            assert len(dashboard_manager.active_connections) == 2

            # Ingest a new sensor reading via REST API
            reading_payload = {
                "device_id": "rover_01",
                "room_id": "room_1",
                "temperature": 22.0,
                "humidity": 46.0,
                "sound_level": 31.0,
                "battery": 95.0,
            }
            res = client.post("/api/sensors/readings", json=reading_payload)
            assert res.status_code == 200

            # 1. Assert Client 1 received broadcast in exact Section 2 shape
            msg_1 = client_1.receive_json()
            assert msg_1["type"] == "sensor_update"
            assert "data" in msg_1
            assert msg_1["data"]["room_id"] == "room_1"
            assert msg_1["data"]["temperature"] == 22.0

            # 2. Assert Client 2 received the same broadcast
            msg_2 = client_2.receive_json()
            assert msg_2["type"] == "sensor_update"
            assert "data" in msg_2
            assert msg_2["data"]["room_id"] == "room_1"
            assert msg_2["data"]["temperature"] == 22.0


def test_dashboard_clients_receive_alert_broadcast_on_recheck_confirmation():
    """Verify that dashboard clients receive alert broadcasts when an anomaly is confirmed."""
    mock_explanation = "Cold temperature confirmed in Bedroom 1 (13.0°C). Check heating."

    with patch("app.workers.anomaly_worker.explain_anomaly_async", new=AsyncMock(return_value=mock_explanation)):
        with client.websocket_connect("/ws/dashboard") as client_ws:
            # 1. First reading: Cold anomaly triggers PENDING recheck
            cold_payload_1 = {
                "device_id": "rover_01",
                "room_id": "room_1",
                "temperature": 13.0,
                "humidity": 45.0,
                "sound_level": 30.0,
                "battery": 94.0,
            }
            client.post("/api/sensors/readings", json=cold_payload_1)

            # Receives sensor_update
            msg1 = client_ws.receive_json()
            assert msg1["type"] == "sensor_update"

            # 2. Second reading (recheck): Anomaly confirmed -> triggers alert broadcast
            cold_payload_2 = {
                "device_id": "rover_01",
                "room_id": "room_1",
                "temperature": 12.8,
                "humidity": 45.0,
                "sound_level": 30.0,
                "battery": 93.5,
            }
            client.post("/api/sensors/readings", json=cold_payload_2)

            # Receives sensor_update first, then alert
            msg_sensor = client_ws.receive_json()
            assert msg_sensor["type"] == "sensor_update"

            msg_alert = client_ws.receive_json()
            assert msg_alert["type"] == "alert"
            assert msg_alert["data"]["room_id"] == "room_1"
            assert msg_alert["data"]["severity"] == "HIGH"
            assert msg_alert["data"]["message"] == mock_explanation
