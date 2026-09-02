"""Unit and integration tests for device token authentication across WebSocket and REST."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import verify_device_token
from app.main import app

client = TestClient(app)


def test_verify_device_token_unit():
    """Verify core verify_device_token function against configured settings."""
    original_token = settings.DEVICE_TOKEN
    try:
        # 1. Configured token
        settings.DEVICE_TOKEN = "hackathon_secret_rover_key_999"
        assert verify_device_token("hackathon_secret_rover_key_999") is True
        assert verify_device_token("wrong_token") is False
        assert verify_device_token("") is False
        assert verify_device_token(None) is False

        # 2. Empty/unset token in dev mode
        settings.DEVICE_TOKEN = ""
        assert verify_device_token("any_token") is True
        assert verify_device_token("") is True
        assert verify_device_token(None) is True
    finally:
        settings.DEVICE_TOKEN = original_token


def test_sensor_ingest_rest_endpoint_auth():
    """Verify REST sensor ingest endpoint rejects invalid token and accepts valid token."""
    original_token = settings.DEVICE_TOKEN
    settings.DEVICE_TOKEN = "secret_hackathon_token_123"

    reading_payload = {
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 35.0,
        "gas_mq2": 20.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 95.0,
    }

    try:
        # 1. Request without token -> Should return 401 UNAUTHORIZED in Section 7 envelope
        res_no_token = client.post("/api/sensors/readings", json=reading_payload)
        assert res_no_token.status_code == 401
        body_no_token = res_no_token.json()
        assert body_no_token["success"] is False
        assert body_no_token["data"] is None
        assert body_no_token["error"]["code"] == "UNAUTHORIZED"

        # 2. Request with wrong token -> Should return 401
        res_wrong = client.post(
            "/api/sensors/readings",
            json=reading_payload,
            headers={"X-Device-Token": "bad_token"},
        )
        assert res_wrong.status_code == 401

        # 3. Request with valid X-Device-Token header -> Should succeed (200)
        res_header = client.post(
            "/api/sensors/readings",
            json=reading_payload,
            headers={"X-Device-Token": "secret_hackathon_token_123"},
        )
        assert res_header.status_code == 200
        assert res_header.json()["success"] is True

        # 4. Request with valid Bearer token -> Should succeed
        res_bearer = client.post(
            "/api/sensors/readings",
            json=reading_payload,
            headers={"Authorization": "Bearer secret_hackathon_token_123"},
        )
        assert res_bearer.status_code == 200
        assert res_bearer.json()["success"] is True

        # 5. Request with query parameter token -> Should succeed
        res_query = client.post(
            "/api/sensors/readings?token=secret_hackathon_token_123",
            json=reading_payload,
        )
        assert res_query.status_code == 200
        assert res_query.json()["success"] is True
    finally:
        settings.DEVICE_TOKEN = original_token


def test_device_websocket_auth_rejection():
    """Verify WebSocket endpoint closes connection when token is invalid or missing."""
    original_token = settings.DEVICE_TOKEN
    settings.DEVICE_TOKEN = "secret_ws_rover_auth_456"

    try:
        # 1. Invalid token query param -> Rejected
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/device/rover_01?token=wrong_ws_token"):
                pass

        # 2. Valid token query param -> Accepted
        with client.websocket_connect("/ws/device/rover_01?token=secret_ws_rover_auth_456") as ws:
            assert ws is not None
    finally:
        settings.DEVICE_TOKEN = original_token
