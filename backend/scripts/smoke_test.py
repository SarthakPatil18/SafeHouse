"""End-to-end smoke test script for SafeRoom backend.

Per AGENTS.md Section 2 (simulation mode) and Prompt specifications:
- Starts the app in-process using TestClient.
- Replays 'gas_leak_mq2' telemetry scenario through the hardware WebSocket ingest path (/ws/device/rover_01).
- Asserts that:
  1. Initial anomaly triggers a PENDING anomaly record.
  2. Sustained anomaly on recheck marks the anomaly CONFIRMED.
  3. A new Alert row is generated and available via /api/alerts.
- Replays 'no_motion_timeout' scenario and asserts the full motion anomaly lifecycle.
- Can be run standalone before demonstrations:
    python scripts/smoke_test.py
  or:
    .venv/bin/python scripts/smoke_test.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.robotics.state_machine import RobotState
from app.services.robot_service import get_state_machine
from app.workers.anomaly_worker import reset_worker_state
from simulation.fake_esp32 import SCENARIO_SCRIPTS


# ANSI Color codes for formatted CLI output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_step(msg: str):
    print(f"{CYAN}{BOLD}[STEP]{RESET} {msg}")


def log_pass(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def log_fail(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def run_smoke_test():
    """Execute complete end-to-end smoke tests for gas and motion anomaly lifecycles."""
    client = TestClient(app)
    sm = get_state_machine()

    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"{BOLD} SafeRoom Backend End-to-End Smoke Test {RESET}")
    print(f"{BOLD}{'='*65}{RESET}\n")

    # -------------------------------------------------------------
    # 1. Health & Server Status Check
    # -------------------------------------------------------------
    log_step("1. Checking server health endpoint (/health)...")
    res_health = client.get("/health")
    assert res_health.status_code == 200, f"Health check failed with {res_health.status_code}"
    health_data = res_health.json()
    assert health_data["success"] is True, "Health check returned success=False"
    log_pass(f"Health check OK: status={health_data['data']['status']}, db_reachable={health_data['data']['db_reachable']}")

    # -------------------------------------------------------------
    # 2. Gas Leak (MQ2) Scenario E2E Pipeline
    # -------------------------------------------------------------
    log_step("2. Replaying 'gas_leak_mq2' scenario through hardware WebSocket route...")
    reset_worker_state()
    sm.state = RobotState.IDLE

    gas_scenario: List[Dict[str, Any]] = SCENARIO_SCRIPTS["gas_leak_mq2"]
    pending_detected = False
    confirmed_detected = False
    confirmed_anomaly_id = None

    with client.websocket_connect("/ws/device/rover_01") as ws:
        log_pass("Connected hardware rover WebSocket to /ws/device/rover_01")

        for idx, reading in enumerate(gas_scenario, start=1):
            ws.send_json(reading)
            ack = ws.receive_json()

            action = ack.get("worker_action")
            is_anomaly = ack.get("is_anomaly")
            mq2_val = reading.get("gas_mq2")

            # Stage A: Initial Anomaly -> PENDING
            if action == "PENDING_RECHECK_TRIGGERED" and not pending_detected:
                pending_detected = True
                log_pass(f"Frame {idx} (MQ2={mq2_val} ppm): PENDING anomaly triggered for {reading['room_id']}")

            # Stage B: Recheck Confirmation -> CONFIRMED & ALERTED
            elif action == "CONFIRMED_AND_ALERTED" and not confirmed_detected:
                confirmed_detected = True
                confirmed_anomaly_id = ack.get("reading_id")
                log_pass(f"Frame {idx} (MQ2={mq2_val} ppm): Anomaly CONFIRMED upon recheck & Alert generated")

    assert pending_detected, "Gas leak did not trigger PENDING state!"
    assert confirmed_detected, "Gas leak was not CONFIRMED on recheck!"

    # Stage C: Query /api/alerts to verify alert presence
    log_step("3. Verifying Alert persistence in /api/alerts...")
    res_alerts = client.get("/api/alerts?status=active")
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()["data"]
    gas_alerts = [a for a in alerts_data if a["room_id"] == "room_4"]
    assert len(gas_alerts) > 0, "No active alert found for room_4!"
    log_pass(f"Alert verified: ID='{gas_alerts[0]['id']}', Severity='{gas_alerts[0]['severity']}'")
    log_pass(f"Message: \"{gas_alerts[0]['message']}\"")

    # -------------------------------------------------------------
    # 3. No Motion Timeout Scenario E2E Pipeline
    # -------------------------------------------------------------
    log_step("4. Replaying 'no_motion_timeout' scenario through WebSocket route...")
    reset_worker_state()
    sm.state = RobotState.IDLE

    motion_scenario: List[Dict[str, Any]] = SCENARIO_SCRIPTS["no_motion_timeout"]
    motion_pending = False
    motion_confirmed = False

    with client.websocket_connect("/ws/device/rover_01") as ws:
        for idx, reading in enumerate(motion_scenario, start=1):
            ws.send_json(reading)
            ack = ws.receive_json()
            action = ack.get("worker_action")

            if action == "PENDING_RECHECK_TRIGGERED" and not motion_pending:
                motion_pending = True
                log_pass(f"Frame {idx}: Inactivity timeout triggered PENDING anomaly in {reading['room_id']}")

            elif action == "CONFIRMED_AND_ALERTED" and not motion_confirmed:
                motion_confirmed = True
                log_pass(f"Frame {idx}: Inactivity anomaly CONFIRMED and Alert generated")

    assert motion_pending, "No-motion timeout did not trigger PENDING state!"
    assert motion_confirmed, "No-motion timeout was not CONFIRMED on recheck!"

    # Stage C: Query /api/alerts to verify motion alert presence
    res_motion_alerts = client.get("/api/alerts?room=room_1")
    assert res_motion_alerts.status_code == 200
    motion_alerts = res_motion_alerts.json()["data"]
    assert len(motion_alerts) > 0, "No alert found for room_1 motion anomaly!"
    log_pass(f"Motion alert verified: ID='{motion_alerts[0]['id']}' Message=\"{motion_alerts[0]['message']}\"")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"{GREEN}{BOLD} ✓ ALL SMOKE TESTS PASSED SUCCESSFULLY! {RESET}")
    print(f"{BOLD} The backend pipeline is ready for presentation and live demo. {RESET}")
    print(f"{BOLD}{'='*65}{RESET}\n")


if __name__ == "__main__":
    try:
        run_smoke_test()
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}{BOLD}Smoke Test Failed:{RESET} {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
