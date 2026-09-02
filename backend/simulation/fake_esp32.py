"""Fake ESP32 hardware simulator and scripted sensor scenario replay.

Per Section 1a, Section 2, and Section 5a of AGENTS.md:
- Replays scripted sensor scenarios:
  1. normal: nominal readings across all rooms
  2. gas_leak_mq2: combustible gas (MQ2) climbing past threshold over several readings
  3. poor_air_quality_mq135: hazardous air quality / pollutant level (MQ135) elevated
  4. no_motion_timeout: expect_presence room with no PIR motion for longer than timeout
  5. unexpected_motion: expect_absence room suddenly detecting PIR motion
  6. sensor_failure: disconnected/malfunctioning hardware sensor readings
  7. device_offline: battery drain leading to device offline state
- Yields readings as a generator for standalone testing or live WebSocket replay.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

# Canonical Scenarios Definition
SCENARIO_SCRIPTS: Dict[str, List[Dict[str, Any]]] = {
    "normal": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 98.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "pir_motion": True,
            "gas_mq135": 30.0,
            "gas_mq2": 18.0,
            "ultrasonic_distance_cm": 115.0,
            "battery": 97.2,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "pir_motion": False,
            "gas_mq135": 25.0,
            "gas_mq2": 15.0,
            "ultrasonic_distance_cm": 140.0,
            "battery": 96.5,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "pir_motion": True,
            "gas_mq135": 45.0,
            "gas_mq2": 30.0,
            "ultrasonic_distance_cm": 95.0,
            "battery": 95.8,
            "status": "PATROLLING",
        },
    ],
    "gas_leak_mq2": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 96.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "pir_motion": False,
            "gas_mq135": 50.0,
            "gas_mq2": 120.0,  # Climbing towards 150.0 ppm threshold
            "ultrasonic_distance_cm": 85.0,
            "battery": 95.5,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "pir_motion": False,
            "gas_mq135": 65.0,
            "gas_mq2": 185.0,  # Climbed past threshold (150.0 ppm) -> triggers gas_mq2_high recheck
            "ultrasonic_distance_cm": 85.0,
            "battery": 95.0,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "pir_motion": False,
            "gas_mq135": 75.0,
            "gas_mq2": 240.0,  # Confirmed severe gas leak climbing further
            "ultrasonic_distance_cm": 85.0,
            "battery": 94.2,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "pir_motion": False,
            "gas_mq135": 45.0,
            "gas_mq2": 70.0,  # Ventilated / resolved
            "ultrasonic_distance_cm": 85.0,
            "battery": 93.5,
            "status": "PATROLLING",
        },
    ],
    "poor_air_quality_mq135": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 95.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "pir_motion": True,
            "gas_mq135": 145.0,  # Elevated MQ135 above 80.0 ppm threshold -> triggers recheck
            "gas_mq2": 22.0,
            "ultrasonic_distance_cm": 110.0,
            "battery": 94.2,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "pir_motion": True,
            "gas_mq135": 180.0,  # Confirmed elevated air quality hazard
            "gas_mq2": 25.0,
            "ultrasonic_distance_cm": 110.0,
            "battery": 93.5,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "pir_motion": True,
            "gas_mq135": 38.0,  # Air returned to normal
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 110.0,
            "battery": 93.0,
            "status": "PATROLLING",
        },
    ],
    "no_motion_timeout": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "no_motion_seconds": 0,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 94.8,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "no_motion_seconds": 1200,  # Inactive but within 3600s timeout
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 94.2,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "no_motion_seconds": 4200,  # Exceeds 3600s timeout in expect_presence room -> triggers recheck
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 93.8,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "no_motion_seconds": 4500,  # Confirmed motion absent too long
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 93.2,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "no_motion_seconds": 0,  # Motion resumes
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 92.8,
            "status": "PATROLLING",
        },
    ],
    "unexpected_motion": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 94.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "pir_motion": False,
            "gas_mq135": 25.0,
            "gas_mq2": 15.0,
            "ultrasonic_distance_cm": 140.0,
            "battery": 93.5,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "pir_motion": True,  # Unexpected motion in expect_absence room -> triggers recheck
            "gas_mq135": 30.0,
            "gas_mq2": 18.0,
            "ultrasonic_distance_cm": 130.0,
            "battery": 93.0,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "pir_motion": True,  # Confirmed unexpected motion
            "gas_mq135": 30.0,
            "gas_mq2": 18.0,
            "ultrasonic_distance_cm": 125.0,
            "battery": 92.4,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "pir_motion": False,  # Quiet room restored
            "gas_mq135": 28.0,
            "gas_mq2": 16.0,
            "ultrasonic_distance_cm": 140.0,
            "battery": 91.8,
            "status": "PATROLLING",
        },
    ],
    "sensor_failure": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 90.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "gas_mq135": -999.0,
            "gas_mq2": -1.0,
            "ultrasonic_distance_cm": -1.0,
            "battery": 89.5,
            "status": "ERROR",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "gas_mq135": None,
            "gas_mq2": None,
            "ultrasonic_distance_cm": 0.0,
            "battery": 89.0,
            "status": "ERROR",
        },
    ],
    "device_offline": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": True,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 12.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "gas_mq135": 35.0,
            "gas_mq2": 20.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 4.0,
            "status": "LOW_BATTERY",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "pir_motion": False,
            "gas_mq135": 0.0,
            "gas_mq2": 0.0,
            "ultrasonic_distance_cm": 0.0,
            "battery": 0.0,
            "status": "OFFLINE",
        },
    ],
}

# Aliases mapping convenience and legacy names to canonical scenarios
SCENARIO_ALIASES = {
    "gas_leak": "gas_leak_mq2",
    "gas leak": "gas_leak_mq2",
    "mq2": "gas_leak_mq2",
    "smoke": "gas_leak_mq2",
    "poor_air_quality": "poor_air_quality_mq135",
    "poor air quality": "poor_air_quality_mq135",
    "gas_hazard": "poor_air_quality_mq135",
    "gas hazard": "poor_air_quality_mq135",
    "gas_hazard_mq135": "poor_air_quality_mq135",
    "air_quality": "poor_air_quality_mq135",
    "air quality": "poor_air_quality_mq135",
    "mq135": "poor_air_quality_mq135",
    "no_motion": "no_motion_timeout",
    "no motion": "no_motion_timeout",
    "no_motion_timeout": "no_motion_timeout",
    "motion_absent": "no_motion_timeout",
    "motion absent": "no_motion_timeout",
    "inactivity": "no_motion_timeout",
    "unexpected_motion": "unexpected_motion",
    "unexpected motion": "unexpected_motion",
    "motion_unexpected": "unexpected_motion",
    "intruder": "unexpected_motion",
    "sensor_failure": "sensor_failure",
    "failure": "sensor_failure",
    "device_offline": "device_offline",
    "offline": "device_offline",
    # Legacy alias support
    "cold_room": "poor_air_quality_mq135",
    "loud_noise": "gas_leak_mq2",
    "humidity_spike": "poor_air_quality_mq135",
}


def list_scenarios() -> List[str]:
    """Return all available canonical scenario names."""
    return list(SCENARIO_SCRIPTS.keys())


def get_scenario_readings(name: str) -> List[Dict[str, Any]]:
    """Retrieve raw scripted sequence for a scenario name.

    Args:
        name: Name of the scenario (e.g. normal, gas_leak_mq2, poor_air_quality_mq135,
              no_motion_timeout, unexpected_motion, sensor_failure, device_offline).

    Returns:
        List of reading dictionaries.

    Raises:
        ValueError: If scenario name is not recognized.
    """
    normalized = name.strip().lower()
    canonical = SCENARIO_ALIASES.get(normalized, normalized)

    if canonical not in SCENARIO_SCRIPTS:
        raise ValueError(
            f"Unknown scenario '{name}'. Available scenarios: {', '.join(list_scenarios())}"
        )

    return SCENARIO_SCRIPTS[canonical]


def run_scenario(
    name: str,
    delay_seconds: float = 0.0,
) -> Generator[Dict[str, Any], None, None]:
    """Yield simulated sensor readings one at a time with optional time delay.

    Args:
        name: Scenario name ('normal', 'gas_leak_mq2', 'poor_air_quality_mq135',
              'no_motion_timeout', 'unexpected_motion', 'sensor_failure', 'device_offline').
        delay_seconds: Time delay in seconds between yielded readings (default 0.0).

    Yields:
        Dictionary formatted according to sensor_readings table schema with fresh UTC timestamp.
    """
    raw_readings = get_scenario_readings(name)

    for step in raw_readings:
        reading = dict(step)
        reading["id"] = f"sim_{uuid.uuid4().hex[:8]}"
        reading["timestamp"] = datetime.now(timezone.utc).isoformat()

        yield reading

        if delay_seconds > 0:
            time.sleep(delay_seconds)


async def run_scenario_async(
    name: str,
    delay_seconds: float = 0.0,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Asynchronously yield simulated sensor readings one at a time for WebSocket streaming.

    Args:
        name: Scenario name.
        delay_seconds: Asynchronous pause between readings in seconds.

    Yields:
        Dictionary with sensor reading payload.
    """
    raw_readings = get_scenario_readings(name)

    for step in raw_readings:
        reading = dict(step)
        reading["id"] = f"sim_{uuid.uuid4().hex[:8]}"
        reading["timestamp"] = datetime.now(timezone.utc).isoformat()

        yield reading

        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
