"""Seed script to populate demo rooms, baselines, device records, and initial alerts.

Run with:
    python scripts/seed_demo_data.py
or:
    .venv/bin/python scripts/seed_demo_data.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path so app modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.db import async_session_factory, check_db_health, init_db
from app.core.logging import logger
from app.models.alert import Alert
from app.models.device import Device
from app.models.room import Room, RoomBaseline
from app.services.room_service import DEFAULT_ROOMS


DEMO_DEVICE = {
    "id": "rover_01",
    "name": "SafeRoom Rover 01",
    "device_type": "rover",
    "status": "IDLE",
    "battery_level": 98.0,
    "firmware_version": "v1.2.0-esp32",
}

DEMO_ROOMS = [
    {
        "id": "room_1",
        "name": "Living Room",
        "type": "living_room",
        "x": 2.0,
        "y": 3.0,
        "order_index": 1,
        "enabled": True,
        "baseline": {
            "gas_mq135_max": 100.0,
            "gas_mq2_max": 100.0,
            "motion_mode": "expect_presence",
            "no_motion_timeout_seconds": 3600,
        },
    },
    {
        "id": "room_2",
        "name": "Master Bedroom",
        "type": "bedroom",
        "x": 6.0,
        "y": 3.0,
        "order_index": 2,
        "enabled": True,
        "baseline": {
            "gas_mq135_max": 80.0,
            "gas_mq2_max": 80.0,
            "motion_mode": "expect_presence",
            "no_motion_timeout_seconds": 28800,
        },
    },
    {
        "id": "room_3",
        "name": "Guest Bedroom",
        "type": "bedroom",
        "x": 6.0,
        "y": 7.0,
        "order_index": 3,
        "enabled": True,
        "baseline": {
            "gas_mq135_max": 80.0,
            "gas_mq2_max": 80.0,
            "motion_mode": "expect_absence",
            "no_motion_timeout_seconds": None,
        },
    },
    {
        "id": "room_4",
        "name": "Kitchen",
        "type": "kitchen",
        "x": 2.0,
        "y": 7.0,
        "order_index": 4,
        "enabled": True,
        "baseline": {
            "gas_mq135_max": 120.0,
            "gas_mq2_max": 150.0,
            "motion_mode": "ignore",
            "no_motion_timeout_seconds": None,
        },
    },
]


async def seed_data():
    """Seed demo database tables with realistic rooms, baselines, and devices."""
    db_alive = await check_db_health()
    if not db_alive:
        print("[INFO] Database connection unavailable (DATABASE_URL offline).")
        print("[INFO] Initializing in-memory demo data structures...")
        for r in DEMO_ROOMS:
            DEFAULT_ROOMS[r["id"]] = r
            print(f"  - Room {r['id']}: {r['name']} (mode: {r['baseline']['motion_mode']}, MQ135 max: {r['baseline']['gas_mq135_max']})")
        print("[SUCCESS] In-memory demo data configured and ready for demo.")
        return

    print("Database connected. Initializing schema tables...")
    await init_db()

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)

        # 1. Seed Device
        print(f"Seeding device: {DEMO_DEVICE['name']} ({DEMO_DEVICE['id']})...")
        res = await session.execute(select(Device).where(Device.id == DEMO_DEVICE["id"]))
        dev = res.scalars().first()
        if not dev:
            dev = Device(
                id=DEMO_DEVICE["id"],
                name=DEMO_DEVICE["name"],
                device_type=DEMO_DEVICE["device_type"],
                status=DEMO_DEVICE["status"],
                battery_level=DEMO_DEVICE["battery_level"],
                firmware_version=DEMO_DEVICE["firmware_version"],
                last_seen=now,
            )
            session.add(dev)
        else:
            dev.status = DEMO_DEVICE["status"]
            dev.battery_level = DEMO_DEVICE["battery_level"]
            dev.last_seen = now

        # 2. Seed Rooms and Baselines
        for r_data in DEMO_ROOMS:
            room_id = r_data["id"]
            print(f"Seeding room: {r_data['name']} ({room_id})...")

            res_r = await session.execute(select(Room).where(Room.id == room_id))
            room = res_r.scalars().first()
            if not room:
                room = Room(
                    id=room_id,
                    name=r_data["name"],
                    type=r_data["type"],
                    x=r_data["x"],
                    y=r_data["y"],
                    order_index=r_data["order_index"],
                    enabled=r_data["enabled"],
                )
                session.add(room)
            else:
                room.name = r_data["name"]
                room.type = r_data["type"]
                room.x = r_data["x"]
                room.y = r_data["y"]
                room.order_index = r_data["order_index"]
                room.enabled = r_data["enabled"]

            # Baseline
            bl_data = r_data["baseline"]
            res_b = await session.execute(
                select(RoomBaseline).where(RoomBaseline.room_id == room_id)
            )
            bl = res_b.scalars().first()
            if not bl:
                bl = RoomBaseline(
                    id=f"bl_{room_id}",
                    room_id=room_id,
                    gas_mq135_max=bl_data["gas_mq135_max"],
                    gas_mq2_max=bl_data["gas_mq2_max"],
                    motion_mode=bl_data["motion_mode"],
                    no_motion_timeout_seconds=bl_data["no_motion_timeout_seconds"],
                    updated_at=now,
                )
                session.add(bl)
            else:
                bl.gas_mq135_max = bl_data["gas_mq135_max"]
                bl.gas_mq2_max = bl_data["gas_mq2_max"]
                bl.motion_mode = bl_data["motion_mode"]
                bl.no_motion_timeout_seconds = bl_data["no_motion_timeout_seconds"]
                bl.updated_at = now

        # 3. Seed Sample Demo Alert
        res_a = await session.execute(select(Alert).where(Alert.id == "alert_demo_1"))
        if not res_a.scalars().first():
            demo_alert = Alert(
                id="alert_demo_1",
                anomaly_id="anom_sample_1",
                room_id="room_3",
                severity="HIGH",
                message="MQ2 combustible gas level in Guest Bedroom elevated to 145.0 ppm, exceeding safe threshold (80.0 ppm).",
                channel="dashboard",
                status="active",
                created_at=now,
                acknowledged_at=None,
            )
            session.add(demo_alert)

        await session.commit()

    print("[SUCCESS] Demo data seeded to Postgres successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
