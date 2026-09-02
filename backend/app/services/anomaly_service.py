"""Deterministic anomaly detection service and severity evaluation.

Per Section 2, Section 5, and Section 5a of AGENTS.md:
- 100% deterministic rule engine using threshold comparisons.
- No dependency on AI or the database (pure functions only).
- Gas anomalies (MQ135 and MQ2) are evaluated independently.
- Gas anomaly severity is NEVER downgraded below MEDIUM.
- Motion anomalies evaluate the 3 motion_mode branches: expect_presence, expect_absence, ignore.
- Pure functions: detect_motion_anomaly accepts last_motion_at from the caller.
- Supported anomaly types: gas_mq135_high, gas_mq2_high, motion_absent_too_long, motion_unexpected.
"""

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class AnomalyType(str, enum.Enum):
    """Standard anomaly type identifiers."""

    GAS_MQ135_HIGH = "gas_mq135_high"
    GAS_MQ2_HIGH = "gas_mq2_high"
    MOTION_ABSENT_TOO_LONG = "motion_absent_too_long"
    MOTION_UNEXPECTED = "motion_unexpected"


class MotionMode(str, enum.Enum):
    """Room motion expectation modes."""

    EXPECT_PRESENCE = "expect_presence"
    EXPECT_ABSENCE = "expect_absence"
    IGNORE = "ignore"
    # Backwards-compatible aliases
    EXPECT_MOTION = "expect_presence"
    EXPECT_NO_MOTION = "expect_absence"


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


def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """Helper to parse a timestamp into a timezone-aware UTC datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        try:
            clean_ts = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None


def get_gas_severity(value: float, threshold: float) -> str:
    """Calculate gas anomaly severity with a floor of MEDIUM.

    Per Section 5a of AGENTS.md:
    Gas anomalies are NEVER downgraded below MEDIUM severity regardless of
    percentage-over-threshold bucketing:
    - deviation > 20% over threshold: "HIGH"
    - deviation <= 20% over threshold: "MEDIUM" (never "LOW")
    """
    if threshold <= 0:
        return "HIGH"

    diff = value - threshold
    if diff <= 0:
        return "MEDIUM"

    ratio = diff / threshold
    if ratio > 0.20:
        return "HIGH"
    return "MEDIUM"


def calculate_severity(difference: float, range_span: float) -> str:
    """Calculate anomaly severity with a floor of MEDIUM per Section 5a."""
    if range_span <= 0:
        return "HIGH"
    ratio = difference / range_span
    if ratio > 0.20:
        return "HIGH"
    return "MEDIUM"


def get_metric_severity(value: float, threshold: float) -> str:
    """Compute severity for a specific anomalous metric value."""
    return get_gas_severity(value, threshold)




def detect_gas_anomaly(
    reading: Any,
    baseline: Any,
) -> List[Dict[str, Any]]:
    """Detect hazardous air quality (MQ135) and combustible gas (MQ2) anomalies independently.

    Per Section 5a of AGENTS.md:
    - Checks gas_mq135 against gas_mq135_max -> type: gas_mq135_high
    - Checks gas_mq2 against gas_mq2_max -> type: gas_mq2_high
    - Gas anomaly severity is NEVER downgraded below MEDIUM (MEDIUM or HIGH only).
    - Boundary rule: Values exactly at threshold (value == threshold) do NOT trigger an anomaly.

    Args:
        reading: Sensor reading dict or model containing gas_mq135 and/or gas_mq2.
        baseline: Room baseline dict or model containing gas_mq135_max and/or gas_mq2_max.

    Returns:
        List of structured anomaly dictionaries for any triggered gas anomalies.
    """
    anomalies: List[Dict[str, Any]] = []

    mq135 = _extract_val(reading, "gas_mq135", "mq135")
    mq2 = _extract_val(reading, "gas_mq2", "mq2")

    mq135_max = _extract_val(baseline, "gas_mq135_max")
    mq2_max = _extract_val(baseline, "gas_mq2_max")

    # 1. MQ135 Air Quality / Hazardous Gas
    if mq135 is not None and mq135_max is not None:
        val_135 = float(mq135)
        thresh_135 = float(mq135_max)
        if val_135 > thresh_135:
            anomalies.append({
                "type": AnomalyType.GAS_MQ135_HIGH.value,
                "severity": get_gas_severity(val_135, thresh_135),
                "value": val_135,
                "expected_min": None,
                "expected_max": thresh_135,
            })

    # 2. MQ2 Combustible Gas / Smoke
    if mq2 is not None and mq2_max is not None:
        val_mq2 = float(mq2)
        thresh_mq2 = float(mq2_max)
        if val_mq2 > thresh_mq2:
            anomalies.append({
                "type": AnomalyType.GAS_MQ2_HIGH.value,
                "severity": get_gas_severity(val_mq2, thresh_mq2),
                "value": val_mq2,
                "expected_min": None,
                "expected_max": thresh_mq2,
            })

    return anomalies


def detect_motion_anomaly(
    reading: Any,
    baseline: Any,
    last_motion_at: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Detect PIR motion anomalies based on room motion mode and timeout.

    Per Section 5a of AGENTS.md:
    Three motion_mode branches:
    1. 'expect_presence' (or 'expect_motion'):
       - If motion detected (pir_motion is True): returns None.
       - If motion absent (pir_motion is False): checks elapsed time since last_motion_at.
         If elapsed_seconds > no_motion_timeout_seconds: returns motion_absent_too_long (severity HIGH).
    2. 'expect_absence' (or 'expect_no_motion'):
       - If motion detected (pir_motion is True): returns motion_unexpected (severity HIGH).
       - If motion absent (pir_motion is False): returns None.
    3. 'ignore':
       - Never triggers any motion anomaly (always returns None).

    Args:
        reading: Sensor reading dict or model containing pir_motion.
        baseline: Room baseline dict or model containing motion_mode and no_motion_timeout_seconds.
        last_motion_at: Optional timestamp of last detected motion (pure function input).

    Returns:
        Structured anomaly dictionary if anomalous, otherwise None.
    """
    pir_motion = _extract_val(reading, "pir_motion", "motion")
    motion_detected = bool(pir_motion) if pir_motion is not None else False

    motion_mode = _extract_val(baseline, "motion_mode", default="expect_presence")
    if isinstance(motion_mode, MotionMode):
        motion_mode = motion_mode.value
    mode_str = str(motion_mode).lower() if motion_mode is not None else "expect_presence"
    no_motion_timeout = _extract_val(baseline, "no_motion_timeout_seconds")
    if no_motion_timeout is not None:
        no_motion_timeout = float(no_motion_timeout)

    # Branch 3: ignore -> Never triggers
    if mode_str == MotionMode.IGNORE.value:
        return None

    # Branch 2: expect_absence -> Unexpected motion detected
    if mode_str in (MotionMode.EXPECT_ABSENCE.value, "expect_no_motion"):
        if motion_detected:
            return {
                "type": AnomalyType.MOTION_UNEXPECTED.value,
                "severity": "HIGH",
                "value": 1.0,
                "expected_min": 0.0,
                "expected_max": 0.0,
            }
        return None

    # Branch 1: expect_presence -> Expected motion absent past timeout
    if mode_str in (MotionMode.EXPECT_PRESENCE.value, "expect_motion"):
        if motion_detected:
            return None

        # Calculate elapsed duration without motion
        elapsed_seconds: Optional[float] = None

        # 1. Direct reading telemetry override (e.g. simulation scenario or smart sensor duration)
        no_motion_sec = _extract_val(
            reading, "no_motion_seconds", "no_motion_duration_seconds", "elapsed_no_motion"
        )
        if no_motion_sec is not None:
            elapsed_seconds = float(no_motion_sec)
        elif _extract_val(reading, "motion_absent_too_long", "motion_absent") is True:
            elapsed_seconds = float(no_motion_timeout + 1) if no_motion_timeout is not None else 301.0
        elif last_motion_at is not None:
            if isinstance(last_motion_at, (int, float)):
                if last_motion_at < 1e9:
                    elapsed_seconds = float(last_motion_at)
                else:
                    last_dt = datetime.fromtimestamp(last_motion_at, tz=timezone.utc)
                    reading_ts = _extract_val(reading, "timestamp")
                    current_dt = _parse_timestamp(reading_ts) or datetime.now(timezone.utc)
                    elapsed_seconds = max(0.0, (current_dt - last_dt).total_seconds())
            else:
                last_dt = _parse_timestamp(last_motion_at)
                if last_dt is not None:
                    reading_ts = _extract_val(reading, "timestamp")
                    current_dt = _parse_timestamp(reading_ts) or datetime.now(timezone.utc)
                    elapsed_seconds = max(0.0, (current_dt - last_dt).total_seconds())


        if (
            elapsed_seconds is not None
            and no_motion_timeout is not None
            and elapsed_seconds > no_motion_timeout
        ):
            return {
                "type": AnomalyType.MOTION_ABSENT_TOO_LONG.value,
                "severity": "HIGH",
                "value": elapsed_seconds,
                "expected_min": 0.0,
                "expected_max": no_motion_timeout,
            }

        return None

    return None


def detect_anomaly(
    reading: Any,
    baseline: Any,
    last_motion_at: Optional[Any] = None,
) -> Tuple[bool, List[str]]:
    """Deterministically check sensor readings against room baseline thresholds.

    Args:
        reading: Object or dict containing pir_motion, gas_mq135, gas_mq2, battery.
        baseline: Object or dict containing gas_mq135_max, gas_mq2_max, motion_mode, no_motion_timeout_seconds.
        last_motion_at: Optional timestamp of last detected motion.

    Returns:
        A tuple of (is_anomaly: bool, anomaly_types: List[str]).
    """
    anomalies: List[str] = []

    gas_anomalies = detect_gas_anomaly(reading, baseline)
    for g in gas_anomalies:
        anomalies.append(g["type"])

    motion_anomaly = detect_motion_anomaly(reading, baseline, last_motion_at=last_motion_at)
    if motion_anomaly is not None:
        anomalies.append(motion_anomaly["type"])

    is_anomaly = len(anomalies) > 0
    return (is_anomaly, anomalies)


def evaluate_reading_anomalies(
    reading: Any,
    baseline: Any,
    last_motion_at: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Evaluate reading against baseline and return detailed anomaly metadata.

    Returns structured dicts matching the `anomalies` table schema in AGENTS.md.
    """
    results: List[Dict[str, Any]] = []

    results.extend(detect_gas_anomaly(reading, baseline))

    motion_anom = detect_motion_anomaly(reading, baseline, last_motion_at=last_motion_at)
    if motion_anom is not None:
        results.append(motion_anom)

    return results
