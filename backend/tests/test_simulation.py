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
    """Verify that all canonical scenarios exist."""
    scenarios = list_scenarios()
    required = [
        "normal",
        "gas_leak_mq2",
        "poor_air_quality_mq135",
        "no_motion_timeout",
        "unexpected_motion",
        "sensor_failure",
        "device_offline",
    ]
    for req in required:
        assert req in scenarios, f"Missing scenario: {req}"


def test_run_scenario_normal():
    """Verify normal scenario yields healthy readings across all rooms."""
    readings = list(run_scenario("normal"))
    assert len(readings) == 4
    for r in readings:
        assert r["device_id"] == "rover_01"
        assert "room_id" in r
        assert "timestamp" in r
        assert "pir_motion" in r
        assert 0.0 <= r["gas_mq135"] <= 100.0
        assert 0.0 <= r["gas_mq2"] <= 100.0
        assert r["ultrasonic_distance_cm"] > 0
        assert r["battery"] > 90.0


def test_run_scenario_poor_air_quality_mq135():
    """Verify poor_air_quality_mq135 scenario triggers gas_mq135_high anomaly."""
    baseline = {
        "gas_mq135_max": 80.0,
        "gas_mq2_max": 80.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 3600,
    }
    readings = list(run_scenario("poor_air_quality_mq135"))
    assert len(readings) >= 3

    # The 2nd reading should trigger gas_mq135_high anomaly (elevated MQ135)
    is_anomaly, anomaly_list = detect_anomaly(readings[1], baseline)
    assert is_anomaly is True
    assert "gas_mq135_high" in anomaly_list


def test_run_scenario_gas_leak_mq2_climbing():
    """Verify gas_leak_mq2 scenario has MQ2 climbing past threshold over several readings."""
    baseline = {
        "gas_mq135_max": 120.0,
        "gas_mq2_max": 150.0,
        "motion_mode": "ignore",
        "no_motion_timeout_seconds": None,
    }
    readings = list(run_scenario("gas_leak_mq2"))
    assert len(readings) >= 4

    # Reading 2 is climbing (120 ppm, below 150)
    is_anom_2, _ = detect_anomaly(readings[1], baseline)
    assert is_anom_2 is False

    # Reading 3 climbs past 150 threshold (185 ppm) -> triggers gas_mq2_high
    is_anom_3, anom_list_3 = detect_anomaly(readings[2], baseline)
    assert is_anom_3 is True
    assert "gas_mq2_high" in anom_list_3

    # Reading 4 climbs further (240 ppm) -> confirmed severe gas leak
    is_anom_4, anom_list_4 = detect_anomaly(readings[3], baseline)
    assert is_anom_4 is True
    assert "gas_mq2_high" in anom_list_4


def test_run_scenario_no_motion_timeout():
    """Verify no_motion_timeout scenario triggers motion_absent_too_long in expect_presence room."""
    baseline = {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 3600,
    }
    readings = list(run_scenario("no_motion_timeout"))
    assert len(readings) >= 4

    # Reading 1: pir_motion=True -> nominal
    is_anom_1, _ = detect_anomaly(readings[0], baseline)
    assert is_anom_1 is False

    # Reading 2: pir_motion=False, 1200s inactive (< 3600s) -> nominal
    is_anom_2, _ = detect_anomaly(readings[1], baseline)
    assert is_anom_2 is False

    # Reading 3: pir_motion=False, 4200s inactive (> 3600s) -> triggers motion_absent_too_long
    is_anom_3, anom_list_3 = detect_anomaly(readings[2], baseline)
    assert is_anom_3 is True
    assert "motion_absent_too_long" in anom_list_3


def test_run_scenario_unexpected_motion():
    """Verify unexpected_motion scenario triggers motion_unexpected in expect_absence room."""
    baseline = {
        "gas_mq135_max": 80.0,
        "gas_mq2_max": 80.0,
        "motion_mode": "expect_absence",
        "no_motion_timeout_seconds": None,
    }
    readings = list(run_scenario("unexpected_motion"))

    # Reading 3 has sudden unexpected motion in room_3
    is_anomaly, anomaly_list = detect_anomaly(readings[2], baseline)
    assert is_anomaly is True
    assert "motion_unexpected" in anomaly_list


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
