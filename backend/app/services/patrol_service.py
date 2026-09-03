"""Service layer for patrol lifecycle, mission state, and room waypoint advancement."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import is_db_connection_error
from app.core.logging import logger
from app.models.patrol import Patrol, PatrolStop
from app.robotics.state_machine import CommandRejectionError, RobotState
from app.schemas.commands import Command, CommandIntent
from app.services.device_manager import get_device_manager
from app.services.robot_service import get_state_machine
from app.services.room_service import RoomService

# In-memory fallback tracking for patrols
_active_patrols: Dict[str, Dict[str, Any]] = {}
_patrol_history: List[Dict[str, Any]] = []


def get_active_patrol(device_id: str = "rover_01") -> Optional[Dict[str, Any]]:
    """Retrieve in-memory active patrol record for a device."""
    return _active_patrols.get(device_id)


def reset_patrol_state() -> None:
    """Reset patrol tracking state for tests."""
    _active_patrols.clear()
    _patrol_history.clear()


class PatrolService:
    """Service handling multi-room patrol sequences and state machine transitions."""

    @staticmethod
    async def start_patrol(
        device_id: str = "rover_01",
        rooms: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Initiate a multi-room patrol sequence.

        Args:
            device_id: Identifier of rover executing patrol.
            rooms: Optional explicit list of room IDs. Defaults to enabled rooms in order_index.
            db: Optional async database session.

        Returns:
            Dictionary with patrol session details.

        Raises:
            CommandRejectionError: If device is in an invalid state (LOW_BATTERY, OFFLINE, OBSTACLE).
        """
        sm = get_state_machine()

        # Enforce Section 4 hard rejection rules
        if sm.state == RobotState.LOW_BATTERY:
            raise CommandRejectionError(
                code="LOW_BATTERY",
                message=f"Cannot start patrol: Rover battery ({sm.battery_level}%) is low.",
            )
        if sm.state == RobotState.OFFLINE:
            raise CommandRejectionError(
                code="ROBOT_OFFLINE",
                message="Cannot start patrol: Rover is currently offline.",
            )
        if sm.has_obstacle:
            raise CommandRejectionError(
                code="OBSTACLE_DETECTED",
                message="Cannot start patrol: Active obstacle detected in path.",
            )

        # Transition state machine to PATROLLING
        sm.execute_command(Command(intent=CommandIntent.START_PATROL))

        # 1. Resolve patrol room sequence
        if not rooms:
            all_rooms = await RoomService.list_rooms(db=db)
            enabled_rooms = [r for r in all_rooms if r.get("enabled", True)]
            enabled_rooms.sort(key=lambda r: r.get("order_index", 0))
            rooms = [r["id"] for r in enabled_rooms]

        if not rooms:
            rooms = ["room_1", "room_2", "room_3", "room_4"]

        # 2. Build structured patrol and patrol_stops records
        patrol_id = f"patrol_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        stops: List[Dict[str, Any]] = []

        for seq, room_id in enumerate(rooms, start=1):
            stops.append({
                "id": f"stop_{uuid.uuid4().hex[:8]}",
                "patrol_id": patrol_id,
                "room_id": room_id,
                "sequence": seq,
                "status": "arrived" if seq == 1 else "pending",
                "arrived_at": now.isoformat() if seq == 1 else None,
                "departed_at": None,
            })

        patrol_data = {
            "id": patrol_id,
            "device_id": device_id,
            "status": "RUNNING",
            "started_at": now.isoformat(),
            "completed_at": None,
            "stops": stops,
            "current_stop_index": 0,
        }

        # 3. Store in-memory
        _active_patrols[device_id] = patrol_data
        _patrol_history.append(patrol_data)

        # 4. Persist to Database if session exists
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
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in PatrolService.start_patrol: %s", e)
                else:
                    logger.error("Database persistence failure in PatrolService.start_patrol: %s", e, exc_info=True)
                    raise

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
    ) -> Dict[str, Any]:
        """Advance patrol to next room stop or complete mission when final room is reached."""
        patrol = _active_patrols.get(device_id)
        if not patrol or patrol["status"] not in ("RUNNING", "IN_PROGRESS"):
            return {"action": "NO_ACTIVE_PATROL", "status": "IDLE"}

        stops = patrol["stops"]
        curr_idx = patrol.get("current_stop_index", 0)
        now = datetime.now(timezone.utc)

        # Mark current stop as departed/completed
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
                    if is_db_connection_error(e):
                        logger.warning("Database connection unavailable in PatrolService.advance_patrol (stop update): %s", e)
                    else:
                        logger.error("Database query failure in PatrolService.advance_patrol: %s", e, exc_info=True)
                        raise

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
                    if is_db_connection_error(e):
                        logger.warning("Database connection unavailable in PatrolService.advance_patrol (completion): %s", e)
                    else:
                        logger.error("Database query failure in PatrolService.advance_patrol: %s", e, exc_info=True)
                        raise

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
                    if is_db_connection_error(e):
                        logger.warning("Database connection unavailable in PatrolService.stop_patrol: %s", e)
                    else:
                        logger.error("Database persistence failure in PatrolService.stop_patrol: %s", e, exc_info=True)
                        raise

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
                return []
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in PatrolService.list_patrols: %s", e)
                else:
                    logger.error("Database query failure in PatrolService.list_patrols: %s", e, exc_info=True)
                    raise

        return list(reversed(_patrol_history[-limit:]))
