"""Deterministic anomaly detection service and severity evaluation.

Per Section 2 and Section 5 of AGENTS.md:
- 100% deterministic rule engine using threshold comparisons.
- No dependency on AI or the database (pure functions only).
"""

from typing import Any, Dict, List, Optional, Tuple


def _extract_val(obj: Any, *keys: str, default: Any = None) -> Any:
    """Helper to extract a field from either a dictionary or object attributes."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
    for k in keys:
        if hasattr(obj, k):
            val = getattr(obj, k)
            if val is not None:
                return val
    return default


def calculate_severity(difference: float, range_span: float) -> str:
    """Calculate anomaly severity based on difference as percentage of expected range.

    Bucketing rules:
    - difference < 10% of range: "LOW"
    - 10% <= difference <= 20% of range: "MEDIUM"
    - difference > 20% of range: "HIGH"

    Args:
        difference: Absolute deviation exceeding the normal boundary.
        range_span: Span of the normal baseline range (e.g., max - min, or threshold).

    Returns:
        "LOW", "MEDIUM", or "HIGH"
    """
    if difference <= 0:
        return "LOW"

    if range_span <= 0:
        return "HIGH"

    ratio = difference / range_span
    if ratio < 0.10:
        return "LOW"
    elif ratio <= 0.20:
        return "MEDIUM"
    else:
        return "HIGH"


def get_metric_severity(
    value: float,
    expected_min: Optional[float] = None,
    expected_max: Optional[float] = None,
    threshold: Optional[float] = None,
) -> str:
    """Compute severity for a specific anomalous metric value.

    Args:
        value: The recorded reading value.
        expected_min: Lower bound of baseline.
        expected_max: Upper bound of baseline.
        threshold: Single upper-bound threshold (e.g. for sound).

    Returns:
        "LOW", "MEDIUM", or "HIGH"
    """
    # Range-bound check (temperature, humidity)
    if expected_min is not None and expected_max is not None:
        range_span = expected_max - expected_min
        if value < expected_min:
            diff = expected_min - value
            return calculate_severity(diff, range_span)
        elif value > expected_max:
            diff = value - expected_max
            return calculate_severity(diff, range_span)
        return "LOW"

    # Single threshold check (sound)
    if threshold is not None:
        if value > threshold:
            diff = value - threshold
            return calculate_severity(diff, threshold)
        return "LOW"

    return "LOW"


def detect_anomaly(
    reading: Any,
    baseline: Any,
) -> Tuple[bool, List[str]]:
    """Deterministically check sensor readings against room baseline thresholds.

    Evaluates:
    - Temperature vs [temperature_min, temperature_max]
    - Humidity vs [humidity_min, humidity_max]
    - Sound level vs sound_threshold

    Boundary rule:
    Values exactly at min/max or threshold are considered normal (not anomalies).

    Args:
        reading: Object or dict containing temperature, humidity, sound_level.
        baseline: Object or dict containing temperature_min, temperature_max,
                  humidity_min, humidity_max, sound_threshold.

    Returns:
        A tuple of (is_anomaly: bool, anomaly_types: List[str]).
    """
    anomalies: List[str] = []

    # Extract reading values
    temp = _extract_val(reading, "temperature", "temp")
    humidity = _extract_val(reading, "humidity")
    sound = _extract_val(reading, "sound_level", "sound")

    # Extract baseline values
    temp_min = _extract_val(baseline, "temperature_min", "temp_min")
    temp_max = _extract_val(baseline, "temperature_max", "temp_max")
    hum_min = _extract_val(baseline, "humidity_min", "hum_min")
    hum_max = _extract_val(baseline, "humidity_max", "hum_max")
    sound_thresh = _extract_val(baseline, "sound_threshold", "sound_thresh")

    # 1. Temperature checks
    if temp is not None:
        if temp_min is not None and temp < temp_min:
            anomalies.append("TEMPERATURE_LOW")
        elif temp_max is not None and temp > temp_max:
            anomalies.append("TEMPERATURE_HIGH")

    # 2. Humidity checks
    if humidity is not None:
        if hum_min is not None and humidity < hum_min:
            anomalies.append("HUMIDITY_LOW")
        elif hum_max is not None and humidity > hum_max:
            anomalies.append("HUMIDITY_HIGH")

    # 3. Sound level check
    if sound is not None and sound_thresh is not None:
        if sound > sound_thresh:
            anomalies.append("SOUND_THRESHOLD_EXCEEDED")

    is_anomaly = len(anomalies) > 0
    return (is_anomaly, anomalies)


def evaluate_reading_anomalies(
    reading: Any,
    baseline: Any,
) -> List[Dict[str, Any]]:
    """Evaluate reading against baseline and return detailed anomaly metadata.

    Returns structured dicts matching the `anomalies` table schema in AGENTS.md.
    """
    results: List[Dict[str, Any]] = []

    temp = _extract_val(reading, "temperature", "temp")
    humidity = _extract_val(reading, "humidity")
    sound = _extract_val(reading, "sound_level", "sound")

    temp_min = _extract_val(baseline, "temperature_min", "temp_min")
    temp_max = _extract_val(baseline, "temperature_max", "temp_max")
    hum_min = _extract_val(baseline, "humidity_min", "hum_min")
    hum_max = _extract_val(baseline, "humidity_max", "hum_max")
    sound_thresh = _extract_val(baseline, "sound_threshold", "sound_thresh")

    # Temperature
    if temp is not None:
        if temp_min is not None and temp < temp_min:
            results.append({
                "type": "TEMPERATURE_LOW",
                "severity": get_metric_severity(temp, expected_min=temp_min, expected_max=temp_max),
                "value": float(temp),
                "expected_min": float(temp_min),
                "expected_max": float(temp_max) if temp_max is not None else None,
            })
        elif temp_max is not None and temp > temp_max:
            results.append({
                "type": "TEMPERATURE_HIGH",
                "severity": get_metric_severity(temp, expected_min=temp_min, expected_max=temp_max),
                "value": float(temp),
                "expected_min": float(temp_min) if temp_min is not None else None,
                "expected_max": float(temp_max),
            })

    # Humidity
    if humidity is not None:
        if hum_min is not None and humidity < hum_min:
            results.append({
                "type": "HUMIDITY_LOW",
                "severity": get_metric_severity(humidity, expected_min=hum_min, expected_max=hum_max),
                "value": float(humidity),
                "expected_min": float(hum_min),
                "expected_max": float(hum_max) if hum_max is not None else None,
            })
        elif hum_max is not None and humidity > hum_max:
            results.append({
                "type": "HUMIDITY_HIGH",
                "severity": get_metric_severity(humidity, expected_min=hum_min, expected_max=hum_max),
                "value": float(humidity),
                "expected_min": float(hum_min) if hum_min is not None else None,
                "expected_max": float(hum_max),
            })

    # Sound
    if sound is not None and sound_thresh is not None and sound > sound_thresh:
        results.append({
            "type": "SOUND_THRESHOLD_EXCEEDED",
            "severity": get_metric_severity(sound, threshold=sound_thresh),
            "value": float(sound),
            "expected_min": None,
            "expected_max": float(sound_thresh),
        })

    return results
