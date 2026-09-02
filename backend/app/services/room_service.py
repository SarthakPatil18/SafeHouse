"""Service layer for room waypoints and environmental baselines."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room, RoomBaseline

# Default in-memory rooms for bootstrap/simulation
DEFAULT_ROOMS: Dict[str, Dict[str, Any]] = {
    "room_1": {
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
    "room_2": {
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
    "room_3": {
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
    "room_4": {
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
}


class RoomService:
    """Service managing rooms and their associated environmental baseline thresholds."""

    @staticmethod
    async def list_rooms(db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
        """List all configured rooms with their current baseline."""
        if db is not None:
            try:
                result = await db.execute(
                    select(Room)
                    .options(selectinload(Room.baseline))
                    .order_by(Room.order_index)
                )
                rooms = result.scalars().all()
                if rooms:
                    return [
                        {
                            "id": r.id,
                            "name": r.name,
                            "type": r.type,
                            "x": r.x,
                            "y": r.y,
                            "order_index": r.order_index,
                            "enabled": r.enabled,
                            "baseline": (
                                {
                                    "gas_mq135_max": r.baseline.gas_mq135_max,
                                    "gas_mq2_max": r.baseline.gas_mq2_max,
                                    "motion_mode": r.baseline.motion_mode,
                                    "no_motion_timeout_seconds": r.baseline.no_motion_timeout_seconds,
                                }
                                if r.baseline
                                else None
                            ),
                        }
                        for r in rooms
                    ]
            except Exception:
                pass

        return list(DEFAULT_ROOMS.values())

    @staticmethod
    async def get_room(
        room_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve details for a single room with its current baseline."""
        if db is not None:
            try:
                result = await db.execute(
                    select(Room)
                    .options(selectinload(Room.baseline))
                    .where(Room.id == room_id)
                )
                r = result.scalars().first()
                if r:
                    return {
                        "id": r.id,
                        "name": r.name,
                        "type": r.type,
                        "x": r.x,
                        "y": r.y,
                        "order_index": r.order_index,
                        "enabled": r.enabled,
                        "baseline": (
                            {
                                "gas_mq135_max": r.baseline.gas_mq135_max,
                                "gas_mq2_max": r.baseline.gas_mq2_max,
                                "motion_mode": r.baseline.motion_mode,
                                "no_motion_timeout_seconds": r.baseline.no_motion_timeout_seconds,
                            }
                            if r.baseline
                            else None
                        ),
                    }
            except Exception:
                pass

        return DEFAULT_ROOMS.get(room_id)

    @staticmethod
    async def create_room(
        room_data: Dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Create a new room waypoint and optional initial baseline."""
        room_id = room_data.get("id") or f"room_{uuid.uuid4().hex[:6]}"
        name = room_data["name"]
        room_type = room_data["type"]
        x = float(room_data.get("x", 0.0))
        y = float(room_data.get("y", 0.0))
        order_index = int(room_data.get("order_index", len(DEFAULT_ROOMS) + 1))
        enabled = bool(room_data.get("enabled", True))
        baseline_data = room_data.get("baseline")

        new_room_dict = {
            "id": room_id,
            "name": name,
            "type": room_type,
            "x": x,
            "y": y,
            "order_index": order_index,
            "enabled": enabled,
            "baseline": baseline_data,
        }
        DEFAULT_ROOMS[room_id] = new_room_dict

        if db is not None:
            try:
                db_room = Room(
                    id=room_id,
                    name=name,
                    type=room_type,
                    x=x,
                    y=y,
                    order_index=order_index,
                    enabled=enabled,
                )
                db.add(db_room)
                if baseline_data:
                    db_bl = RoomBaseline(
                        id=f"bl_{uuid.uuid4().hex[:8]}",
                        room_id=room_id,
                        gas_mq135_max=baseline_data.get("gas_mq135_max", 100.0),
                        gas_mq2_max=baseline_data.get("gas_mq2_max", 100.0),
                        motion_mode=baseline_data.get("motion_mode", "expect_presence"),
                        no_motion_timeout_seconds=baseline_data.get("no_motion_timeout_seconds"),
                    )
                    db.add(db_bl)
                await db.commit()
            except Exception:
                pass

        return new_room_dict

    @staticmethod
    async def update_room(
        room_id: str,
        update_data: Dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update room waypoint metadata."""
        if room_id in DEFAULT_ROOMS:
            for k, v in update_data.items():
                if v is not None and k in DEFAULT_ROOMS[room_id]:
                    DEFAULT_ROOMS[room_id][k] = v

        if db is not None:
            try:
                result = await db.execute(
                    select(Room)
                    .options(selectinload(Room.baseline))
                    .where(Room.id == room_id)
                )
                db_room = result.scalars().first()
                if db_room:
                    for k, v in update_data.items():
                        if v is not None and hasattr(db_room, k):
                            setattr(db_room, k, v)
                    await db.commit()
            except Exception:
                pass

        return await RoomService.get_room(room_id, db=db)

    @staticmethod
    async def delete_room(
        room_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Delete a room and its associated baseline."""
        found = False
        if room_id in DEFAULT_ROOMS:
            del DEFAULT_ROOMS[room_id]
            found = True

        if db is not None:
            try:
                result = await db.execute(select(Room).where(Room.id == room_id))
                db_room = result.scalars().first()
                if db_room:
                    await db.delete(db_room)
                    await db.commit()
                    found = True
            except Exception:
                pass

        return found

    @staticmethod
    async def update_baseline(
        room_id: str,
        baseline_data: Dict[str, Any],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Update or create baseline thresholds for a room."""
        # Normalize motion_mode aliases if passed
        raw_mode = baseline_data.get("motion_mode", "expect_presence")
        if raw_mode == "expect_motion":
            raw_mode = "expect_presence"
        elif raw_mode == "expect_no_motion":
            raw_mode = "expect_absence"
        baseline_data["motion_mode"] = raw_mode

        # If motion_mode is not expect_presence, no_motion_timeout_seconds is None
        if raw_mode != "expect_presence":
            baseline_data["no_motion_timeout_seconds"] = None

        if room_id in DEFAULT_ROOMS:
            if DEFAULT_ROOMS[room_id].get("baseline") is None:
                DEFAULT_ROOMS[room_id]["baseline"] = {}
            DEFAULT_ROOMS[room_id]["baseline"].update(baseline_data)

        if db is not None:
            try:
                result = await db.execute(
                    select(RoomBaseline).where(RoomBaseline.room_id == room_id)
                )
                bl = result.scalars().first()
                if bl:
                    for k, v in baseline_data.items():
                        if hasattr(bl, k):
                            setattr(bl, k, v)
                    bl.updated_at = datetime.now(timezone.utc)
                else:
                    bl = RoomBaseline(
                        id=f"bl_{uuid.uuid4().hex[:8]}",
                        room_id=room_id,
                        gas_mq135_max=baseline_data.get("gas_mq135_max", 100.0),
                        gas_mq2_max=baseline_data.get("gas_mq2_max", 100.0),
                        motion_mode=baseline_data.get("motion_mode", "expect_presence"),
                        no_motion_timeout_seconds=baseline_data.get("no_motion_timeout_seconds"),
                    )
                    db.add(bl)
                await db.commit()
            except Exception:
                pass

        return DEFAULT_ROOMS.get(room_id, {}).get("baseline", baseline_data)
