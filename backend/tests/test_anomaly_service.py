"""Unit tests for deterministic anomaly detection and Section 5a rules."""

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.anomaly_service import (
    AnomalyType,
    MotionMode,
    detect_anomaly,
    detect_gas_anomaly,
    detect_motion_anomaly,
    evaluate_reading_anomalies,
    get_gas_severity,
)


def get_default_baseline():
    """Standard baseline for room tests."""
    return {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 3600,
    }


# Pytest fixture support
try:
    import pytest

    @pytest.fixture
    def baseline():
        return get_default_baseline()
except ImportError:
    pass


def test_mq135_over_threshold():
    """Verify MQ135 hazardous gas level exceeding gas_mq135_max triggers gas_mq135_high."""
    baseline = {"gas_mq135_max": 100.0, "gas_mq2_max": 100.0}
    reading = {"gas_mq135": 105.0, "gas_mq2": 25.0, "pir_motion": True}

    # 1. Test detect_gas_anomaly
    gas_anomalies = detect_gas_anomaly(reading, baseline)
    assert len(gas_anomalies) == 1
    assert gas_anomalies[0]["type"] == "gas_mq135_high"
    assert gas_anomalies[0]["value"] == 105.0
    assert gas_anomalies[0]["expected_max"] == 100.0

    # 2. Test detect_anomaly
    is_anom, types = detect_anomaly(reading, baseline)
    assert is_anom is True
    assert "gas_mq135_high" in types


def test_mq2_over_threshold():
    """Verify MQ2 combustible gas level exceeding gas_mq2_max triggers gas_mq2_high."""
    baseline = {"gas_mq135_max": 100.0, "gas_mq2_max": 80.0}
    reading = {"gas_mq135": 40.0, "gas_mq2": 150.0, "pir_motion": True}

    # 1. Test detect_gas_anomaly
    gas_anomalies = detect_gas_anomaly(reading, baseline)
    assert len(gas_anomalies) == 1
    assert gas_anomalies[0]["type"] == "gas_mq2_high"
    assert gas_anomalies[0]["value"] == 150.0
    assert gas_anomalies[0]["expected_max"] == 80.0

    # 2. Test detect_anomaly
    is_anom, types = detect_anomaly(reading, baseline)
    assert is_anom is True
    assert "gas_mq2_high" in types


def test_motion_absent_past_timeout_expect_presence():
    """Verify motion absent past timeout triggers motion_absent_too_long when mode=expect_presence."""
    baseline = {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 1800,  # 30 minutes
    }
    now = datetime.now(timezone.utc)
    reading = {"pir_motion": False, "timestamp": now.isoformat()}

    # Motion detected 45 minutes ago -> exceeds 30m timeout
    last_motion_at = now - timedelta(minutes=45)
    motion_anom = detect_motion_anomaly(reading, baseline, last_motion_at=last_motion_at)
    assert motion_anom is not None
    assert motion_anom["type"] == "motion_absent_too_long"
    assert motion_anom["severity"] == "HIGH"
    assert motion_anom["value"] >= 2700.0

    # Test within timeout (motion detected 10 minutes ago) -> no anomaly
    recent_motion_at = now - timedelta(minutes=10)
    normal_motion = detect_motion_anomaly(reading, baseline, last_motion_at=recent_motion_at)
    assert normal_motion is None

    # Test when motion is active (pir_motion=True) -> no anomaly
    active_reading = {"pir_motion": True, "timestamp": now.isoformat()}
    assert detect_motion_anomaly(active_reading, baseline, last_motion_at=last_motion_at) is None


def test_unexpected_motion_expect_absence():
    """Verify unexpected motion triggers motion_unexpected when mode=expect_absence."""
    baseline = {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "expect_absence",
        "no_motion_timeout_seconds": None,
    }
    reading_motion = {"pir_motion": True}
    anom = detect_motion_anomaly(reading_motion, baseline)
    assert anom is not None
    assert anom["type"] == "motion_unexpected"
    assert anom["severity"] == "HIGH"
    assert anom["value"] == 1.0

    # No motion in expect_absence -> nominal
    reading_quiet = {"pir_motion": False}
    assert detect_motion_anomaly(reading_quiet, baseline) is None


def test_motion_mode_ignore_never_triggers():
    """Verify motion_mode=ignore NEVER triggers any motion anomaly under any condition."""
    baseline = {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "ignore",
        "no_motion_timeout_seconds": 60,
    }
    now = datetime.now(timezone.utc)

    # 1. Motion detected in ignore mode
    reading_motion = {"pir_motion": True}
    assert detect_motion_anomaly(reading_motion, baseline) is None

    # 2. No motion for 10 hours in ignore mode
    reading_no_motion = {"pir_motion": False, "timestamp": now.isoformat()}
    long_ago = now - timedelta(hours=10)
    assert detect_motion_anomaly(reading_no_motion, baseline, last_motion_at=long_ago) is None


def test_boundary_case_exactly_at_threshold():
    """Verify exact threshold boundary: value == threshold must NOT trigger an anomaly."""
    baseline = {
        "gas_mq135_max": 100.0,
        "gas_mq2_max": 100.0,
        "motion_mode": "expect_presence",
        "no_motion_timeout_seconds": 3600,
    }
    exact_reading = {
        "gas_mq135": 100.0,  # Exactly at threshold
        "gas_mq2": 100.0,    # Exactly at threshold
        "pir_motion": True,
    }

    gas_anomalies = detect_gas_anomaly(exact_reading, baseline)
    assert gas_anomalies == []

    is_anom, types = detect_anomaly(exact_reading, baseline)
    assert is_anom is False
    assert types == []


def test_gas_severity_never_downgraded_below_medium():
    """Verify Section 5a rule: Gas anomalies are NEVER downgraded below MEDIUM."""
    threshold = 100.0

    # 1% above threshold (101.0 ppm) -> deviation = 1% (< 10%)
    # Standard bucketing would have given LOW, but Section 5a requires minimum of MEDIUM
    assert get_gas_severity(101.0, threshold) == "MEDIUM"

    # 5% above threshold (105.0 ppm) -> MEDIUM
    assert get_gas_severity(105.0, threshold) == "MEDIUM"

    # 15% above threshold (115.0 ppm) -> MEDIUM
    assert get_gas_severity(115.0, threshold) == "MEDIUM"

    # 20% exactly above threshold (120.0 ppm) -> MEDIUM
    assert get_gas_severity(120.0, threshold) == "MEDIUM"

    # > 20% above threshold (125.0 ppm) -> HIGH
    assert get_gas_severity(125.0, threshold) == "HIGH"
    assert get_gas_severity(200.0, threshold) == "HIGH"


def test_multiple_gas_anomalies_independent():
    """Verify MQ135 and MQ2 anomalies are evaluated independently."""
    baseline = {"gas_mq135_max": 80.0, "gas_mq2_max": 60.0}
    reading = {"gas_mq135": 120.0, "gas_mq2": 90.0, "pir_motion": True}

    anomalies = detect_gas_anomaly(reading, baseline)
    assert len(anomalies) == 2
    types = [a["type"] for a in anomalies]
    assert "gas_mq135_high" in types
    assert "gas_mq2_high" in types


def test_object_attribute_access():
    """Ensure pure functions work with class instances and objects as well as dicts."""
    class MockReading:
        pir_motion = True
        gas_mq135 = 150.0
        gas_mq2 = 30.0

    class MockBaseline:
        gas_mq135_max = 100.0
        gas_mq2_max = 100.0
        motion_mode = "expect_presence"
        no_motion_timeout_seconds = 3600

    is_anomaly, anomaly_list = detect_anomaly(MockReading(), MockBaseline())
    assert is_anomaly is True
    assert anomaly_list == ["gas_mq135_high"]


if __name__ == "__main__":
    test_mq135_over_threshold()
    test_mq2_over_threshold()
    test_motion_absent_past_timeout_expect_presence()
    test_unexpected_motion_expect_absence()
    test_motion_mode_ignore_never_triggers()
    test_boundary_case_exactly_at_threshold()
    test_gas_severity_never_downgraded_below_medium()
    test_multiple_gas_anomalies_independent()
    test_object_attribute_access()
    print("All anomaly service tests passed successfully!")
