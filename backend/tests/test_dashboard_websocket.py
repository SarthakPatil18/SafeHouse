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
                "pir_motion": True,
                "gas_mq135": 38.0,
                "gas_mq2": 22.0,
                "ultrasonic_distance_cm": 115.0,
                "battery": 95.0,
            }
            res = client.post("/api/sensors/readings", json=reading_payload)
            assert res.status_code == 200

            # 1. Assert Client 1 received broadcast in exact Section 2 shape
            msg_1 = client_1.receive_json()
            assert msg_1["type"] == "sensor_update"
            assert "data" in msg_1
            assert msg_1["data"]["room_id"] == "room_1"
            assert msg_1["data"]["gas_mq135"] == 38.0

            # 2. Assert Client 2 received the same broadcast
            msg_2 = client_2.receive_json()
            assert msg_2["type"] == "sensor_update"
            assert "data" in msg_2
            assert msg_2["data"]["room_id"] == "room_1"
            assert msg_2["data"]["gas_mq135"] == 38.0


def test_dashboard_clients_receive_alert_broadcast_on_recheck_confirmation():
    """Verify that dashboard clients receive alert broadcasts when an anomaly is confirmed."""
    mock_explanation = "Elevated hazardous gas confirmed in Living Room (160.0 ppm). Check ventilation."

    with patch("app.workers.anomaly_worker.explain_anomaly_async", new=AsyncMock(return_value=mock_explanation)):
        with client.websocket_connect("/ws/dashboard") as client_ws:
            # 1. First reading: MQ135 gas anomaly triggers PENDING recheck
            gas_payload_1 = {
                "device_id": "rover_01",
                "room_id": "room_1",
                "pir_motion": True,
                "gas_mq135": 160.0,
                "gas_mq2": 30.0,
                "ultrasonic_distance_cm": 110.0,
                "battery": 94.0,
            }
            client.post("/api/sensors/readings", json=gas_payload_1)

            # Receives sensor_update
            msg1 = client_ws.receive_json()
            assert msg1["type"] == "sensor_update"

            # 2. Second reading (recheck): Anomaly confirmed -> triggers alert broadcast
            gas_payload_2 = {
                "device_id": "rover_01",
                "room_id": "room_1",
                "pir_motion": True,
                "gas_mq135": 175.0,
                "gas_mq2": 30.0,
                "ultrasonic_distance_cm": 110.0,
                "battery": 93.5,
            }
            client.post("/api/sensors/readings", json=gas_payload_2)

            # Receives sensor_update first, then alert
            msg_sensor = client_ws.receive_json()
            assert msg_sensor["type"] == "sensor_update"

            msg_alert = client_ws.receive_json()
            assert msg_alert["type"] == "alert"
            assert msg_alert["data"]["room_id"] == "room_1"
            assert msg_alert["data"]["severity"] == "HIGH"
            assert msg_alert["data"]["message"] == mock_explanation

