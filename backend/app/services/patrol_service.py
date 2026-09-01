"""Service layer for patrol mission lifecycle, waypoint stops, and rover command orchestration."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.patrol import Patrol, PatrolStop
from app.robotics.state_machine import CommandRejectionError, RobotState
from app.schemas.commands import Command, CommandIntent
from app.services.device_manager import get_device_manager
from app.services.robot_service import RobotService, get_state_machine
from app.services.room_service import RoomService

# In-memory active patrol state tracking
_active_patrols: Dict[str, Dict[str, Any]] = {}
_patrol_history: List[Dict[str, Any]] = []


def get_active_patrol(device_id: str = "rover_01") -> Optional[Dict[str, Any]]:
    """Return active patrol dictionary for a device."""
    return _active_patrols.get(device_id)


def reset_patrol_state() -> None:
    """Reset in-memory patrol state."""
    _active_patrols.clear()
    _patrol_history.clear()


class PatrolService:
    """Service managing autonomous and manual rover patrol missions."""

    @staticmethod
    async def start_patrol(
        device_id: str = "rover_01",
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Start a new patrol across enabled rooms, checking Section 4 rejection rules.

        1. Enforces Section 4 rejection rules (LOW_BATTERY, OFFLINE, OBSTACLE).
        2. Creates a patrols record (status='RUNNING') and patrol_stops for enabled rooms.
        3. Sends the first GO_TO_ROOM command to the rover via WebSocket.

        Raises:
            CommandRejectionError: If device is in LOW_BATTERY or OFFLINE state.
        """
        sm = get_state_machine()

        # 1. Check Section 4 Rejection Rules
        cmd = Command(intent=CommandIntent.START_PATROL)
        sm.validate_command(cmd)
        sm.execute_command(cmd)

        # 2. Fetch enabled rooms sorted by order_index
        all_rooms = await RoomService.list_rooms(db=db)
        enabled_rooms = [r for r in all_rooms if r.get("enabled", True)]
        enabled_rooms.sort(key=lambda r: r.get("order_index", 0))

        if not enabled_rooms:
            raise CommandRejectionError(
                code="NO_ENABLED_ROOMS",
                message="Cannot start patrol: No enabled rooms configured.",
            )

        patrol_id = f"patrol_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        # 3. Create patrol stops
        stops: List[Dict[str, Any]] = []
        for idx, room in enumerate(enabled_rooms, start=1):
            stop_id = f"stop_{idx}_{uuid.uuid4().hex[:4]}"
            stops.append({
                "id": stop_id,
                "patrol_id": patrol_id,
                "room_id": room["id"],
                "room_name": room.get("name", room["id"]),
                "sequence": idx,
                "status": "arrived" if idx == 1 else "pending",
                "arrived_at": now.isoformat() if idx == 1 else None,
                "departed_at": None,
            })

        patrol_data = {
            "id": patrol_id,
            "device_id": device_id,
            "status": "RUNNING",
            "started_at": now.isoformat(),
            "completed_at": None,
            "current_stop_index": 0,
            "stops": stops,
        }

        _active_patrols[device_id] = patrol_data
        _patrol_history.append(patrol_data)

        # 4. Persist to DB if available
        if db is not None:
            try:
                db_patrol = Patrol(
                    id=patrol_id,
                    device_id=device_id,
                    status="RUNNING",
                    started_at=now,
                )
                db.add(db_patrol)
                for s in stops:
                    db_stop = PatrolStop(
                        id=s["id"],
                        patrol_id=patrol_id,
                        room_id=s["room_id"],
                        sequence=s["sequence"],
                        status=s["status"],
                        arrived_at=now if s["sequence"] == 1 else None,
                    )
                    db.add(db_stop)
                await db.commit()
            except Exception as e:
                logger.debug("Database patrol creation deferred (%s).", e)

        # 5. Dispatch first GO_TO_ROOM command to the rover via WebSocket
        first_room = stops[0]["room_id"]
        sm.current_room_id = first_room
        await get_device_manager().send_command(
            device_id=device_id,
            command_dict={
                "intent": "GO_TO_ROOM",
                "room_id": first_room,
                "priority": "normal",
                "confirmation_required": False,
            },
        )

        return patrol_data

    @staticmethod
    async def advance_patrol(
        device_id: str = "rover_01",
        room_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Advance patrol after a room inspection finishes.

        Marks current stop departed_at, sends next GO_TO_ROOM, or triggers RETURN_HOME
        if the last room was visited.
        """
        patrol = _active_patrols.get(device_id)
        if not patrol or patrol.get("status") != "RUNNING":
            return None

        now = datetime.now(timezone.utc)
        curr_idx = patrol.get("current_stop_index", 0)
        stops = patrol.get("stops", [])

        if curr_idx < len(stops):
            current_stop = stops[curr_idx]
            current_stop["status"] = "completed"
            current_stop["departed_at"] = now.isoformat()

            # Update DB stop record if available
            if db is not None:
                try:
                    res = await db.execute(select(PatrolStop).where(PatrolStop.id == current_stop["id"]))
                    db_stop = res.scalars().first()
                    if db_stop:
                        db_stop.status = "completed"
                        db_stop.departed_at = now
                        await db.commit()
                except Exception as e:
                    logger.debug("Database patrol stop update deferred (%s).", e)

        next_idx = curr_idx + 1
        sm = get_state_machine()

        if next_idx < len(stops):
            # Advance to next room stop
            patrol["current_stop_index"] = next_idx
            next_stop = stops[next_idx]
            next_stop["status"] = "arrived"
            next_stop["arrived_at"] = now.isoformat()
            next_room = next_stop["room_id"]

            sm.current_room_id = next_room
            sm.transition_to(RobotState.PATROLLING)

            await get_device_manager().send_command(
                device_id=device_id,
                command_dict={
                    "intent": "GO_TO_ROOM",
                    "room_id": next_room,
                    "priority": "normal",
                    "confirmation_required": False,
                },
            )

            return {
                "action": "ADVANCED_TO_NEXT_ROOM",
                "next_room_id": next_room,
                "current_stop_index": next_idx,
                "patrol": patrol,
            }

        else:
            # All stops completed -> Mark patrol COMPLETED and RETURN_HOME
            patrol["status"] = "COMPLETED"
            patrol["completed_at"] = now.isoformat()
            _active_patrols.pop(device_id, None)

            # Update DB patrol record
            if db is not None:
                try:
                    res = await db.execute(select(Patrol).where(Patrol.id == patrol["id"]))
                    db_patrol = res.scalars().first()
                    if db_patrol:
                        db_patrol.status = "COMPLETED"
                        db_patrol.completed_at = now
                        await db.commit()
                except Exception as e:
                    logger.debug("Database patrol completion deferred (%s).", e)

            # Transition state machine and dispatch RETURN_HOME command
            sm.execute_command(Command(intent=CommandIntent.RETURN_HOME))

            await get_device_manager().send_command(
                device_id=device_id,
                command_dict={
                    "intent": "RETURN_HOME",
                    "priority": "normal",
                    "confirmation_required": False,
                },
            )

            return {
                "action": "PATROL_COMPLETED_RETURN_HOME",
                "patrol": patrol,
            }

    @staticmethod
    async def stop_patrol(
        device_id: str = "rover_01",
        patrol_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Mark active patrol CANCELLED and immediately issue STOP_ROVER interrupt."""
        sm = get_state_machine()

        # Execute immediate emergency stop interrupt
        sm.execute_command(Command(intent=CommandIntent.STOP_ROVER, priority="high"))

        # Send STOP_ROVER command to rover via WebSocket
        await get_device_manager().send_command(
            device_id=device_id,
            command_dict={
                "intent": "STOP_ROVER",
                "priority": "high",
                "confirmation_required": False,
            },
        )

        now = datetime.now(timezone.utc)
        patrol = _active_patrols.pop(device_id, None)

        if patrol:
            patrol["status"] = "CANCELLED"
            patrol["completed_at"] = now.isoformat()

            if db is not None:
                try:
                    res = await db.execute(select(Patrol).where(Patrol.id == patrol["id"]))
                    db_patrol = res.scalars().first()
                    if db_patrol:
                        db_patrol.status = "CANCELLED"
                        db_patrol.completed_at = now
                        await db.commit()
                except Exception as e:
                    logger.debug("Database patrol cancellation deferred (%s).", e)

            return patrol

        return {
            "device_id": device_id,
            "status": "CANCELLED",
            "completed_at": now.isoformat(),
        }

    @staticmethod
    async def list_patrols(
        limit: int = 20,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """List historical and active patrol missions."""
        if db is not None:
            try:
                result = await db.execute(
                    select(Patrol)
                    .options(selectinload(Patrol.stops))
                    .order_by(desc(Patrol.started_at))
                    .limit(limit)
                )
                records = result.scalars().all()
                if records:
                    return [
                        {
                            "id": p.id,
                            "device_id": p.device_id,
                            "status": p.status,
                            "started_at": p.started_at.isoformat(),
                            "completed_at": (
                                p.completed_at.isoformat()
                                if p.completed_at
                                else None
                            ),
                            "stops": [
                                {
                                    "id": s.id,
                                    "room_id": s.room_id,
                                    "sequence": s.sequence,
                                    "status": s.status,
                                    "arrived_at": (
                                        s.arrived_at.isoformat()
                                        if s.arrived_at
                                        else None
                                    ),
                                    "departed_at": (
                                        s.departed_at.isoformat()
                                        if s.departed_at
                                        else None
                                    ),
                                }
                                for s in p.stops
                            ],
                        }
                        for p in records
                    ]
            except Exception:
                pass

        return list(reversed(_patrol_history[-limit:]))
