"""Unit tests for deterministic anomaly detection and severity calculation."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.anomaly_service import (
    calculate_severity,
    detect_anomaly,
    evaluate_reading_anomalies,
    get_metric_severity,
)


def get_default_baseline():
    """Standard baseline for room tests: temp [18-24 C], humidity [40-60%], sound max 50 dB."""
    return {
        "temperature_min": 18.0,
        "temperature_max": 24.0,
        "humidity_min": 40.0,
        "humidity_max": 60.0,
        "sound_threshold": 50.0,
    }


# Pytest fixture support if pytest is installed
try:
    import pytest

    @pytest.fixture
    def baseline():
        return get_default_baseline()
except ImportError:
    pass


def test_normal_reading(baseline=None):
    """Test reading where all metrics are within safe baseline bounds."""
    b = baseline or get_default_baseline()
    reading = {
        "temperature": 21.0,
        "humidity": 50.0,
        "sound_level": 35.0,
    }
    is_anomaly, anomaly_list = detect_anomaly(reading, b)
    assert is_anomaly is False
    assert anomaly_list == []

    detailed = evaluate_reading_anomalies(reading, b)
    assert detailed == []


def test_low_temperature(baseline=None):
    """Test reading with temperature dropped below temperature_min."""
    b = baseline or get_default_baseline()
    reading = {
        "temperature": 15.0,  # Below min 18.0 (diff 3.0 on span 6.0 = 50% -> HIGH)
        "humidity": 50.0,
        "sound_level": 30.0,
    }
    is_anomaly, anomaly_list = detect_anomaly(reading, b)
    assert is_anomaly is True
    assert "TEMPERATURE_LOW" in anomaly_list
    assert len(anomaly_list) == 1

    detailed = evaluate_reading_anomalies(reading, b)
    assert len(detailed) == 1
    assert detailed[0]["type"] == "TEMPERATURE_LOW"
    assert detailed[0]["severity"] == "HIGH"
    assert detailed[0]["value"] == 15.0


def test_high_humidity(baseline=None):
    """Test reading with humidity spiking above humidity_max."""
    b = baseline or get_default_baseline()
    reading = {
        "temperature": 21.0,
        "humidity": 75.0,  # Above max 60.0 (diff 15.0 on span 20.0 = 75% -> HIGH)
        "sound_level": 40.0,
    }
    is_anomaly, anomaly_list = detect_anomaly(reading, b)
    assert is_anomaly is True
    assert "HUMIDITY_HIGH" in anomaly_list
    assert len(anomaly_list) == 1

    detailed = evaluate_reading_anomalies(reading, b)
    assert len(detailed) == 1
    assert detailed[0]["type"] == "HUMIDITY_HIGH"
    assert detailed[0]["severity"] == "HIGH"


def test_loud_sound(baseline=None):
    """Test reading with loud noise exceeding sound_threshold."""
    b = baseline or get_default_baseline()
    reading = {
        "temperature": 20.0,
        "humidity": 50.0,
        "sound_level": 80.0,  # Above threshold 50.0 (diff 30.0 on span 50.0 = 60% -> HIGH)
    }
    is_anomaly, anomaly_list = detect_anomaly(reading, b)
    assert is_anomaly is True
    assert "SOUND_THRESHOLD_EXCEEDED" in anomaly_list
    assert len(anomaly_list) == 1

    detailed = evaluate_reading_anomalies(reading, b)
    assert len(detailed) == 1
    assert detailed[0]["type"] == "SOUND_THRESHOLD_EXCEEDED"
    assert detailed[0]["severity"] == "HIGH"


def test_multiple_simultaneous_anomalies(baseline=None):
    """Test reading with simultaneous low temp, high humidity, and loud sound."""
    b = baseline or get_default_baseline()
    reading = {
        "temperature": 14.0,  # Low temp
        "humidity": 85.0,     # High humidity
        "sound_level": 95.0,  # Loud sound
    }
    is_anomaly, anomaly_list = detect_anomaly(reading, b)
    assert is_anomaly is True
    assert len(anomaly_list) == 3
    assert "TEMPERATURE_LOW" in anomaly_list
    assert "HUMIDITY_HIGH" in anomaly_list
    assert "SOUND_THRESHOLD_EXCEEDED" in anomaly_list

    detailed = evaluate_reading_anomalies(reading, b)
    assert len(detailed) == 3


def test_boundary_values_at_exact_min_max(baseline=None):
    """Test boundary conditions: exact min/max/threshold values must NOT trigger anomalies."""
    b = baseline or get_default_baseline()

    # Test at lower boundaries
    min_reading = {
        "temperature": 18.0,  # Exactly at min
        "humidity": 40.0,     # Exactly at min
        "sound_level": 0.0,
    }
    is_anomaly, anomaly_list = detect_anomaly(min_reading, b)
    assert is_anomaly is False
    assert anomaly_list == []

    # Test at upper boundaries
    max_reading = {
        "temperature": 24.0,  # Exactly at max
        "humidity": 60.0,     # Exactly at max
        "sound_level": 50.0,  # Exactly at threshold
    }
    is_anomaly, anomaly_list = detect_anomaly(max_reading, b)
    assert is_anomaly is False
    assert anomaly_list == []


def test_severity_bucketing():
    """Verify severity bucketing: <10% = LOW, 10-20% = MEDIUM, >20% = HIGH."""
    range_span = 100.0

    # < 10%
    assert calculate_severity(5.0, range_span) == "LOW"
    assert calculate_severity(9.9, range_span) == "LOW"

    # 10% - 20%
    assert calculate_severity(10.0, range_span) == "MEDIUM"
    assert calculate_severity(15.0, range_span) == "MEDIUM"
    assert calculate_severity(20.0, range_span) == "MEDIUM"

    # > 20%
    assert calculate_severity(20.1, range_span) == "HIGH"
    assert calculate_severity(50.0, range_span) == "HIGH"


def test_metric_severity_temperature_and_humidity():
    """Verify get_metric_severity calculations for range-bounded metrics."""
    # Temperature range: 20 to 30 (range_span = 10.0)
    # 0.5 diff (5%) -> LOW
    assert get_metric_severity(19.5, expected_min=20.0, expected_max=30.0) == "LOW"
    # 1.5 diff (15%) -> MEDIUM
    assert get_metric_severity(31.5, expected_min=20.0, expected_max=30.0) == "MEDIUM"
    # 2.5 diff (25%) -> HIGH
    assert get_metric_severity(32.5, expected_min=20.0, expected_max=30.0) == "HIGH"


def test_object_attribute_access():
    """Ensure detect_anomaly works with class instances / Pydantic objects as well as dicts."""
    class MockReading:
        temperature = 12.0
        humidity = 50.0
        sound_level = 30.0

    class MockBaseline:
        temperature_min = 18.0
        temperature_max = 24.0
        humidity_min = 40.0
        humidity_max = 60.0
        sound_threshold = 50.0

    is_anomaly, anomaly_list = detect_anomaly(MockReading(), MockBaseline())
    assert is_anomaly is True
    assert anomaly_list == ["TEMPERATURE_LOW"]


if __name__ == "__main__":
    test_normal_reading()
    test_low_temperature()
    test_high_humidity()
    test_loud_sound()
    test_multiple_simultaneous_anomalies()
    test_boundary_values_at_exact_min_max()
    test_severity_bucketing()
    test_metric_severity_temperature_and_humidity()
    test_object_attribute_access()
    print("All 9 anomaly service tests passed successfully!")
