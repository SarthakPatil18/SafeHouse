"""Fake ESP32 hardware simulator and scripted sensor scenario replay.

Per Section 2 of AGENTS.md:
- Replays scripted sensor scenarios (normal / cold room / loud sound / humidity spike /
  sensor failure / offline) so the backend is fully demoable with zero hardware connected.
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
            "temperature": 21.5,
            "humidity": 45.0,
            "sound_level": 30.0,
            "battery": 98.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "temperature": 22.0,
            "humidity": 48.0,
            "sound_level": 32.0,
            "battery": 97.2,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "temperature": 21.0,
            "humidity": 46.5,
            "sound_level": 28.0,
            "battery": 96.5,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "temperature": 20.8,
            "humidity": 47.0,
            "sound_level": 31.0,
            "battery": 95.8,
            "status": "PATROLLING",
        },
    ],
    "cold_room": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 45.0,
            "sound_level": 30.0,
            "battery": 96.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "temperature": 18.5,
            "humidity": 44.0,
            "sound_level": 31.0,
            "battery": 95.2,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "temperature": 14.2,  # Cold anomaly below 18°C
            "humidity": 42.0,
            "sound_level": 28.0,
            "battery": 94.5,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_3",
            "temperature": 12.5,  # Confirmed severe cold
            "humidity": 41.0,
            "sound_level": 27.0,
            "battery": 93.8,
            "status": "RECHECKING",
        },
    ],
    "loud_noise": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 48.0,
            "sound_level": 32.0,
            "battery": 95.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "temperature": 21.2,
            "humidity": 49.0,
            "sound_level": 88.5,  # Loud noise anomaly (> 50 dB)
            "battery": 94.2,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "temperature": 21.3,
            "humidity": 48.5,
            "sound_level": 94.0,  # Loud sound spike
            "battery": 93.5,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_2",
            "temperature": 21.0,
            "humidity": 48.0,
            "sound_level": 35.0,  # Sound returns to ambient
            "battery": 93.0,
            "status": "PATROLLING",
        },
    ],
    "humidity_spike": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 45.0,
            "sound_level": 30.0,
            "battery": 94.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "temperature": 22.5,
            "humidity": 78.0,  # Humidity anomaly above 60%
            "sound_level": 34.0,
            "battery": 93.2,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "temperature": 23.0,
            "humidity": 89.0,  # Severe humidity spike
            "sound_level": 35.0,
            "battery": 92.5,
            "status": "RECHECKING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_4",
            "temperature": 22.8,
            "humidity": 92.0,  # Peak humidity
            "sound_level": 33.0,
            "battery": 91.8,
            "status": "RECHECKING",
        },
    ],
    "sensor_failure": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 48.0,
            "sound_level": 30.0,
            "battery": 90.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": -999.0,
            "humidity": -1.0,
            "sound_level": -1.0,
            "battery": 89.5,
            "status": "ERROR",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": None,
            "humidity": None,
            "sound_level": 0.0,
            "battery": 89.0,
            "status": "ERROR",
        },
    ],
    "device_offline": [
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 45.0,
            "sound_level": 30.0,
            "battery": 12.0,
            "status": "PATROLLING",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 20.8,
            "humidity": 45.0,
            "sound_level": 30.0,
            "battery": 4.0,
            "status": "LOW_BATTERY",
        },
        {
            "device_id": "rover_01",
            "room_id": "room_1",
            "temperature": 0.0,
            "humidity": 0.0,
            "sound_level": 0.0,
            "battery": 0.0,
            "status": "OFFLINE",
        },
    ],
}

# Aliases for convenience
SCENARIO_ALIASES = {
    "cold room": "cold_room",
    "cold": "cold_room",
    "loud sound": "loud_noise",
    "loud": "loud_noise",
    "noise": "loud_noise",
    "humidity": "humidity_spike",
    "failure": "sensor_failure",
    "offline": "device_offline",
}


def list_scenarios() -> List[str]:
    """Return all available scenario names."""
    return list(SCENARIO_SCRIPTS.keys())


def get_scenario_readings(name: str) -> List[Dict[str, Any]]:
    """Retrieve raw scripted sequence for a scenario name.

    Args:
        name: Name of the scenario (e.g. normal, cold_room, loud_noise).

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
        name: Scenario name ('normal', 'cold_room', 'loud_noise', 'humidity_spike',
              'sensor_failure', 'device_offline').
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
