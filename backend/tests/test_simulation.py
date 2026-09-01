"""Unit tests for fake ESP32 hardware simulator and scenario generators."""

import asyncio
import pytest

from app.services.anomaly_service import detect_anomaly
from simulation.fake_esp32 import (
    get_scenario_readings,
    list_scenarios,
    run_scenario,
    run_scenario_async,
)


def test_list_scenarios_contains_all_required_scenarios():
    """Verify that all 6 required scenarios from AGENTS.md Section 2 exist."""
    scenarios = list_scenarios()
    required = [
        "normal",
        "cold_room",
        "loud_noise",
        "humidity_spike",
        "sensor_failure",
        "device_offline",
    ]
    for req in required:
        assert req in scenarios, f"Missing scenario: {req}"


def test_run_scenario_normal():
    """Verify normal scenario yields healthy readings."""
    readings = list(run_scenario("normal"))
    assert len(readings) == 4
    for r in readings:
        assert r["device_id"] == "rover_01"
        assert "room_id" in r
        assert "timestamp" in r
        assert 18.0 <= r["temperature"] <= 24.0
        assert 40.0 <= r["humidity"] <= 60.0
        assert r["sound_level"] <= 50.0
        assert r["battery"] > 90.0


def test_run_scenario_cold_room():
    """Verify cold_room scenario triggers temperature anomalies."""
    baseline = {
        "temperature_min": 18.0,
        "temperature_max": 24.0,
        "humidity_min": 40.0,
        "humidity_max": 60.0,
        "sound_threshold": 50.0,
    }
    readings = list(run_scenario("cold_room"))
    assert len(readings) >= 3

    # The 3rd reading should trigger a low temperature anomaly
    is_anomaly, anomaly_list = detect_anomaly(readings[2], baseline)
    assert is_anomaly is True
    assert "TEMPERATURE_LOW" in anomaly_list


def test_run_scenario_loud_noise():
    """Verify loud_noise scenario triggers sound threshold anomaly."""
    baseline = {
        "temperature_min": 18.0,
        "temperature_max": 24.0,
        "humidity_min": 40.0,
        "humidity_max": 60.0,
        "sound_threshold": 50.0,
    }
    readings = list(run_scenario("loud_noise"))
    assert len(readings) >= 3

    # Reading 2 has high sound
    is_anomaly, anomaly_list = detect_anomaly(readings[1], baseline)
    assert is_anomaly is True
    assert "SOUND_THRESHOLD_EXCEEDED" in anomaly_list


def test_run_scenario_humidity_spike():
    """Verify humidity_spike scenario triggers high humidity anomaly."""
    baseline = {
        "temperature_min": 18.0,
        "temperature_max": 24.0,
        "humidity_min": 40.0,
        "humidity_max": 60.0,
        "sound_threshold": 50.0,
    }
    readings = list(run_scenario("humidity_spike"))

    # Reading 2 has high humidity
    is_anomaly, anomaly_list = detect_anomaly(readings[1], baseline)
    assert is_anomaly is True
    assert "HUMIDITY_HIGH" in anomaly_list


def test_run_scenario_sensor_failure_and_offline():
    """Verify sensor failure and offline state representation."""
    fail_readings = list(run_scenario("sensor_failure"))
    assert any(r.get("status") == "ERROR" for r in fail_readings)

    offline_readings = list(run_scenario("device_offline"))
    assert any(r.get("status") == "OFFLINE" for r in offline_readings)


def test_unknown_scenario_raises_value_error():
    """Verify invalid scenario name raises a descriptive ValueError."""
    with pytest.raises(ValueError) as exc_info:
        list(run_scenario("unknown_random_scenario"))
    assert "Unknown scenario" in str(exc_info.value)


def test_run_scenario_async():
    """Verify async generator streaming capability."""
    async def _test():
        items = []
        async for r in run_scenario_async("normal"):
            items.append(r)
        assert len(items) == 4

    asyncio.run(_test())
