"""Service layer for room waypoints and environmental baselines."""

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
            "temperature_min": 18.0,
            "temperature_max": 24.0,
            "humidity_min": 40.0,
            "humidity_max": 60.0,
            "sound_threshold": 50.0,
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
            "temperature_min": 19.0,
            "temperature_max": 23.0,
            "humidity_min": 40.0,
            "humidity_max": 55.0,
            "sound_threshold": 45.0,
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
            "temperature_min": 18.0,
            "temperature_max": 24.0,
            "humidity_min": 40.0,
            "humidity_max": 60.0,
            "sound_threshold": 50.0,
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
            "temperature_min": 18.0,
            "temperature_max": 26.0,
            "humidity_min": 35.0,
            "humidity_max": 65.0,
            "sound_threshold": 60.0,
        },
    },
}


class RoomService:
    """Service managing rooms and their associated environmental baseline thresholds."""

    @staticmethod
    async def list_rooms(db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
        """List all configured rooms."""
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
                                    "temperature_min": r.baseline.temperature_min,
                                    "temperature_max": r.baseline.temperature_max,
                                    "humidity_min": r.baseline.humidity_min,
                                    "humidity_max": r.baseline.humidity_max,
                                    "sound_threshold": r.baseline.sound_threshold,
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
        """Retrieve details for a single room."""
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
                                "temperature_min": r.baseline.temperature_min,
                                "temperature_max": r.baseline.temperature_max,
                                "humidity_min": r.baseline.humidity_min,
                                "humidity_max": r.baseline.humidity_max,
                                "sound_threshold": r.baseline.sound_threshold,
                            }
                            if r.baseline
                            else None
                        ),
                    }
            except Exception:
                pass

        return DEFAULT_ROOMS.get(room_id)

    @staticmethod
    async def update_baseline(
        room_id: str,
        baseline_data: Dict[str, float],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Update or set baseline thresholds for a room."""
        if room_id in DEFAULT_ROOMS:
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
                        room_id=room_id,
                        temperature_min=baseline_data.get("temperature_min", 18.0),
                        temperature_max=baseline_data.get("temperature_max", 24.0),
                        humidity_min=baseline_data.get("humidity_min", 40.0),
                        humidity_max=baseline_data.get("humidity_max", 60.0),
                        sound_threshold=baseline_data.get("sound_threshold", 50.0),
                    )
                    db.add(bl)
                await db.commit()
            except Exception:
                pass

        return DEFAULT_ROOMS.get(room_id, {}).get("baseline", baseline_data)
