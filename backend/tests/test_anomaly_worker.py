"""Unit and integration tests for AnomalyWorker recheck confirmation and alert pipeline."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.robotics.state_machine import RobotState
from app.services.robot_service import get_state_machine
from app.workers.anomaly_worker import (
    AnomalyWorker,
    get_created_alerts,
    get_pending_anomalies,
    reset_worker_state,
)

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


@pytest.mark.anyio
async def test_anomaly_then_confirm_on_recheck_creates_alert():
    """Verify 2-step pipeline: PENDING on first detection -> CONFIRMED & ALERT on recheck."""
    sm = get_state_machine()
    sm.state = RobotState.PATROLLING

    # 1. First Reading: MQ135 gas anomaly in room_1 (baseline max: 100.0 ppm)
    first_reading = {
        "id": "sr_test_1",
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 160.0,  # Above safe max 100.0
        "gas_mq2": 30.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 95.0,
    }

    res_1 = await AnomalyWorker.process_reading(first_reading)
    assert res_1["action"] == "PENDING_RECHECK_TRIGGERED"
    assert res_1["status"] == "PENDING"
    assert "room_1" in get_pending_anomalies()
    assert sm.state == RobotState.RECHECKING

    # Ensure NO alert was created on initial detection
    assert len(get_created_alerts()) == 0

    # 2. Second Reading (Recheck): Anomaly still present
    recheck_reading = {
        "id": "sr_test_2",
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 175.0,  # Still high
        "gas_mq2": 30.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 94.5,
    }

    mock_explanation = "Elevated hazardous gas detected in Living Room (175.0 ppm). Please inspect room ventilation."
    with patch("app.workers.anomaly_worker.explain_anomaly_async", new=AsyncMock(return_value=mock_explanation)) as mock_ai:
        res_2 = await AnomalyWorker.process_reading(recheck_reading)

        # Assert anomaly confirmed and alert created
        assert res_2["action"] == "CONFIRMED_AND_ALERTED"
        assert res_2["status"] == "CONFIRMED"
        assert len(get_created_alerts()) == 1

        alert = get_created_alerts()[0]
        assert alert["room_id"] == "room_1"
        assert alert["severity"] == "HIGH"
        assert alert["message"] == mock_explanation
        assert alert["status"] == "active"

        # State machine should have returned to IDLE after concluding recheck
        assert sm.state == RobotState.IDLE
        assert "room_1" not in get_pending_anomalies()
        mock_ai.assert_called_once()


@pytest.mark.anyio
async def test_anomaly_then_resolve_on_recheck_no_alert():
    """Verify 2-step pipeline: PENDING on first detection -> RESOLVED without alert on healthy recheck."""
    sm = get_state_machine()
    sm.state = RobotState.PATROLLING

    # 1. First Reading: MQ2 gas spike in room_2 (baseline max: 80.0 ppm)
    first_reading = {
        "id": "sr_test_gas",
        "device_id": "rover_01",
        "room_id": "room_2",
        "pir_motion": True,
        "gas_mq135": 30.0,
        "gas_mq2": 150.0,  # Combustible gas spike
        "ultrasonic_distance_cm": 110.0,
        "battery": 95.0,
    }

    res_1 = await AnomalyWorker.process_reading(first_reading)
    assert res_1["action"] == "PENDING_RECHECK_TRIGGERED"
    assert sm.state == RobotState.RECHECKING
    assert len(get_created_alerts()) == 0

    # 2. Second Reading (Recheck): Gas returned to normal ambient level
    healthy_recheck_reading = {
        "id": "sr_test_normal",
        "device_id": "rover_01",
        "room_id": "room_2",
        "pir_motion": True,
        "gas_mq135": 30.0,
        "gas_mq2": 25.0,  # Normal MQ2 <= 80.0 ppm
        "ultrasonic_distance_cm": 110.0,
        "battery": 94.8,
    }

    with patch("app.workers.anomaly_worker.explain_anomaly_async") as mock_ai:
        res_2 = await AnomalyWorker.process_reading(healthy_recheck_reading)

        # Assert anomaly resolved and NO alert created
        assert res_2["action"] == "RESOLVED_NO_ALERT"
        assert res_2["status"] == "RESOLVED"
        assert len(get_created_alerts()) == 0
        mock_ai.assert_not_called()
        assert sm.state == RobotState.IDLE
        assert "room_2" not in get_pending_anomalies()


@pytest.mark.anyio
async def test_multiple_simultaneous_anomalies_confirm_creates_multiple_alerts():
    """Verify multiple simultaneous anomaly types per reading (e.g. MQ135 + MQ2) create multiple alerts."""
    sm = get_state_machine()
    sm.state = RobotState.PATROLLING

    # 1. First Reading: Simultaneous MQ135 and MQ2 gas anomalies in room_1
    first_reading = {
        "id": "sr_test_multi_1",
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 160.0,  # Above 100 max
        "gas_mq2": 170.0,    # Above 100 max
        "ultrasonic_distance_cm": 120.0,
        "battery": 95.0,
    }

    res_1 = await AnomalyWorker.process_reading(first_reading)
    assert res_1["action"] == "PENDING_RECHECK_TRIGGERED"
    assert res_1["anomaly_count"] == 2
    assert "room_1" in get_pending_anomalies()
    assert sm.state == RobotState.RECHECKING

    # 2. Second Reading (Recheck): Both anomalies confirmed
    recheck_reading = {
        "id": "sr_test_multi_2",
        "device_id": "rover_01",
        "room_id": "room_1",
        "pir_motion": True,
        "gas_mq135": 170.0,
        "gas_mq2": 180.0,
        "ultrasonic_distance_cm": 120.0,
        "battery": 94.0,
    }

    mock_explanation = "Simultaneous hazardous and combustible gas confirmed in Living Room."
    with patch("app.workers.anomaly_worker.explain_anomaly_async", new=AsyncMock(return_value=mock_explanation)):
        res_2 = await AnomalyWorker.process_reading(recheck_reading)

        assert res_2["action"] == "CONFIRMED_AND_ALERTED"
        assert res_2["confirmed_count"] == 2
        assert len(get_created_alerts()) == 2
        alert_types = [a["severity"] for a in get_created_alerts()]
        assert len(alert_types) == 2


def test_websocket_stream_recheck_confirmation_flow():
    """Integration test: Verify WebSocket client receives worker action flags across recheck cycle."""
    mock_explanation = "Unexpected motion confirmed in Guest Bedroom. Verify room."

    with patch("app.workers.anomaly_worker.explain_anomaly_async", new=AsyncMock(return_value=mock_explanation)):
        with client.websocket_connect("/ws/device/rover_01") as ws:
            # 1. First bad reading -> Triggers PENDING_RECHECK_TRIGGERED (room_3 mode is expect_no_motion)
            ws.send_json({
                "device_id": "rover_01",
                "room_id": "room_3",
                "pir_motion": True,
                "gas_mq135": 30.0,
                "gas_mq2": 20.0,
                "ultrasonic_distance_cm": 120.0,
                "battery": 95.0,
            })
            ack1 = ws.receive_json()
            assert ack1["is_anomaly"] is True
            assert ack1["worker_action"] == "PENDING_RECHECK_TRIGGERED"
            assert ack1["robot_state"] == "RECHECKING"

            # 2. Second bad reading (recheck) -> Triggers CONFIRMED_AND_ALERTED
            ws.send_json({
                "device_id": "rover_01",
                "room_id": "room_3",
                "pir_motion": True,
                "gas_mq135": 30.0,
                "gas_mq2": 20.0,
                "ultrasonic_distance_cm": 120.0,
                "battery": 94.5,
            })
            ack2 = ws.receive_json()
            assert ack2["is_anomaly"] is True
            assert ack2["worker_action"] == "CONFIRMED_AND_ALERTED"
            assert ack2["robot_state"] == "IDLE"
