"""Unit and integration tests for ESP32 hardware WebSocket transport."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.main import app
from app.robotics.state_machine import RobotState
from app.services.robot_service import get_state_machine
from app.services.sensor_service import SensorService

client = TestClient(app)


def test_websocket_auth_rejection():
    """Verify that WebSocket rejects connection when wrong token is provided."""
    # Temporarily enforce a strict device token
    original_token = settings.DEVICE_TOKEN
    settings.DEVICE_TOKEN = "secret_rover_auth_123"

    try:
        # Connect with invalid token -> should fail
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/device/rover_01?token=wrong_token"):
                pass

        # Connect with valid token -> should succeed
        with client.websocket_connect("/ws/device/rover_01?token=secret_rover_auth_123") as ws:
            assert ws is not None
    finally:
        settings.DEVICE_TOKEN = original_token


def test_websocket_connect_lifecycle_and_normal_reading():
    """Verify CONNECTED/DISCONNECTED events and telemetry ingestion via WebSocket."""
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    sm.has_obstacle = False
    sm.battery_level = 98.0

    with client.websocket_connect("/ws/device/rover_01") as ws:
        # State machine should be brought online
        assert sm.state == RobotState.IDLE

        # Send normal sensor reading payload
        payload = {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 97.0,
        }
        ws.send_json(payload)

        # Receive acknowledgment
        response = ws.receive_json()
        assert response["status"] == "acknowledged"
        assert response["is_anomaly"] is False
        assert response["anomalies"] == []
        assert "reading_id" in response

    # On disconnect, state machine is marked OFFLINE
    assert sm.state == RobotState.OFFLINE


def test_websocket_anomaly_detection_on_bad_reading():
    """Verify that known-bad readings trigger anomaly detection and flag over WebSocket."""
    with client.websocket_connect("/ws/device/rover_01") as ws:
        # Send hazardous gas anomaly payload in room_1 (baseline max is 100.0 ppm)
        bad_payload = {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 180.0,  # 180.0 ppm is well above safe 100.0 ppm maximum
            "gas_mq2": 30.0,
            "ultrasonic_distance_cm": 110.0,
            "battery": 92.0,
        }
        ws.send_json(bad_payload)

        # Receive acknowledgment
        response = ws.receive_json()
        assert response["status"] == "acknowledged"
        assert response["is_anomaly"] is True
        assert "gas_mq135_high" in response["anomalies"]

        # Verify reading is also stored and available via SensorService
        latest = client.get("/api/sensors/latest")
        assert latest.status_code == 200
        assert latest.json()["data"]["gas_mq135"] == 180.0

