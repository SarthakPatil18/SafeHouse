"""Live test client verifying the complete anomaly -> confirm -> alert -> live dashboard WebSocket pipeline."""

import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import websockets
from simulation.fake_esp32 import SCENARIO_SCRIPTS


async def run_live_e2e_pipeline_verification():
    dashboard_url = "ws://127.0.0.1:8000/ws/dashboard"
    device_url = "ws://127.0.0.1:8000/ws/device/rover_01"

    dashboard_messages = []
    dashboard_ready = asyncio.Event()

    print("\n" + "=" * 70)
    print(" LIVE DASHBOARD WEBSOCKET PIPELINE VERIFICATION")
    print("=" * 70 + "\n")

    async def dashboard_client():
        print(f"[1] Connecting Dashboard Client to {dashboard_url}...")
        async with websockets.connect(dashboard_url) as ws:
            print("[✓] Dashboard client connected successfully.")
            dashboard_ready.set()

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    parsed = json.loads(msg)
                    dashboard_messages.append(parsed)
                    msg_type = parsed.get("type", "unknown")
                    print(f"\n>>> [DASHBOARD WS RECEIVED: {msg_type.upper()}] <<<")
                    print(json.dumps(parsed, indent=2))
                except asyncio.TimeoutError:
                    print("\n[INFO] Dashboard listener timeout reached (no more messages received).")
                    break

    async def device_simulator():
        await dashboard_ready.wait()
        await asyncio.sleep(0.5)

        print(f"\n[2] Connecting Hardware Simulator to {device_url}...")
        async with websockets.connect(device_url) as ws:
            print("[✓] Hardware simulator connected successfully.")
            scenario = SCENARIO_SCRIPTS["gas_leak_mq2"]
            print(f"[INFO] Streaming {len(scenario)} telemetry frames from 'gas_leak_mq2' scenario...\n")

            for i, reading in enumerate(scenario, 1):
                await ws.send(json.dumps(reading))
                ack = await ws.recv()
                ack_data = json.loads(ack)
                print(f"  --> Sent Frame {i} (Room: {reading['room_id']}, MQ2: {reading['gas_mq2']} ppm) | ACK: {ack_data.get('worker_action')}")
                await asyncio.sleep(0.3)

    # Run both concurrently
    await asyncio.gather(
        dashboard_client(),
        device_simulator(),
    )

    print("\n" + "=" * 70)
    print(" VERIFICATION SUMMARY")
    print("=" * 70)
    types_received = [m.get("type") for m in dashboard_messages]
    print(f"Total messages received on /ws/dashboard: {len(dashboard_messages)}")
    print(f"Message types received: {types_received}")

    sensor_updates = [m for m in dashboard_messages if m.get("type") == "sensor_update"]
    alerts = [m for m in dashboard_messages if m.get("type") == "alert"]

    print(f"Sensor updates count: {len(sensor_updates)}")
    print(f"Alerts count: {len(alerts)}")

    assert len(sensor_updates) > 0, "No sensor_update message received on /ws/dashboard!"
    assert len(alerts) > 0, "No alert message received on /ws/dashboard!"

    print("\n[SUCCESS] Anomaly -> Confirm -> Alert -> Live Dashboard push verified end-to-end!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_live_e2e_pipeline_verification())
