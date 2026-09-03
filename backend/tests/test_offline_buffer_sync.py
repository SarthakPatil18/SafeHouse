"""Unit and integration tests for offline buffer sync (POST /api/sensors/sync).

Per Section 5b:
1. Ingest batch of offline buffered sensor readings.
2. Ensure readings are processed in chronological order even if received out-of-order.
3. Mark persisted readings with source='buffered'.
4. Ensure alerts generated from buffered data have message prefixed with
   "Detected from offline buffered data: ".
5. Return persisted indices and synced count in API envelope.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.robotics.state_machine import RobotState
from app.services.robot_service import get_state_machine
from app.workers.anomaly_worker import get_created_alerts, reset_worker_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset worker and state machine state before each test."""
    reset_worker_state()
    sm = get_state_machine()
    sm.state = RobotState.IDLE
    sm.has_obstacle = False
    sm.current_room_id = None
    yield
    reset_worker_state()


def test_offline_sync_chronological_batch_and_alert_prefix():
    """Verify syncing a chronological batch marks source='buffered' and prefixes alert message."""
    headers = {"X-Device-Token": settings.DEVICE_TOKEN} if settings.DEVICE_TOKEN else {}

    # Batch of 3 chronological readings in room_4 (Kitchen: MQ2 max baseline is 100.0 ppm)
    readings_batch = [
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T10:00:00Z",
            "pir_motion": False,
            "gas_mq135": 30.0,
            "gas_mq2": 20.0,  # Normal
            "ultrasonic_distance_cm": 150.0,
            "battery": 90.0,
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T10:00:05Z",
            "pir_motion": False,
            "gas_mq135": 35.0,
            "gas_mq2": 180.0,  # Anomaly! Triggers PENDING_RECHECK
            "ultrasonic_distance_cm": 150.0,
            "battery": 90.0,
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T10:00:10Z",
            "pir_motion": False,
            "gas_mq135": 40.0,
            "gas_mq2": 195.0,  # Recheck confirmed! Triggers Alert
            "ultrasonic_distance_cm": 150.0,
            "battery": 89.5,
        },
    ]

    response = client.post("/api/sensors/sync", json=readings_batch, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["synced_count"] == 3
    assert data["persisted_indices"] == [0, 1, 2]

    # Verify all persisted rows have source='buffered'
    for r in data["readings"]:
        assert r["source"] == "buffered"

    # Verify alert created by the batch has the required offline buffer prefix
    alerts = get_created_alerts()
    assert len(alerts) >= 1
    buffered_alert = alerts[-1]
    assert buffered_alert["room_id"] == "room_4"
    assert buffered_alert["message"].startswith("Detected from offline buffered data: ")


def test_offline_sync_out_of_order_timestamps():
    """Verify out-of-order input readings are sorted and processed in chronological order."""
    headers = {"X-Device-Token": settings.DEVICE_TOKEN} if settings.DEVICE_TOKEN else {}

    # Provided in out-of-order timestamps: [Recheck, Initial Spike, Normal Baseline]
    out_of_order_batch = [
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T12:00:10Z",  # Step 3: Recheck (timestamp latest)
            "pir_motion": False,
            "gas_mq135": 30.0,
            "gas_mq2": 210.0,
            "ultrasonic_distance_cm": 150.0,
            "battery": 88.0,
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T12:00:05Z",  # Step 2: Initial Spike (middle timestamp)
            "pir_motion": False,
            "gas_mq135": 30.0,
            "gas_mq2": 175.0,
            "ultrasonic_distance_cm": 150.0,
            "battery": 88.5,
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "timestamp": "2026-09-03T12:00:00Z",  # Step 1: Normal (earliest timestamp)
            "pir_motion": False,
            "gas_mq135": 30.0,
            "gas_mq2": 15.0,
            "ultrasonic_distance_cm": 150.0,
            "battery": 89.0,
        },
    ]

    response = client.post("/api/sensors/sync", json=out_of_order_batch, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["synced_count"] == 3
    # Sorted order was index 2 (earliest), then 1, then 0 (latest)
    assert data["persisted_indices"] == [2, 1, 0]

    # Verify chronological sequence: first reading had mq2=15.0, second 175.0, third 210.0
    assert data["readings"][0]["gas_mq2"] == 15.0
    assert data["readings"][1]["gas_mq2"] == 175.0
    assert data["readings"][2]["gas_mq2"] == 210.0

    # Verify alert created upon chronological recheck
    alerts = get_created_alerts()
    assert len(alerts) >= 1
    assert alerts[-1]["message"].startswith("Detected from offline buffered data: ")


def test_offline_sync_empty_payload():
    """Verify empty sync batch returns clean empty success envelope."""
    headers = {"X-Device-Token": settings.DEVICE_TOKEN} if settings.DEVICE_TOKEN else {}
    response = client.post("/api/sensors/sync", json=[], headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["synced_count"] == 0
    assert payload["data"]["persisted_indices"] == []
