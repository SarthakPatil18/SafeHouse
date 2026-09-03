"""Service layer for robot operations, telemetry status, and command execution."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import is_db_connection_error
from app.core.logging import logger
from app.models.device import Device, RobotEvent
from app.robotics.state_machine import (
    CommandRejectionError,
    RobotState,
    RobotStateMachine,
)
from app.schemas.commands import Command, CommandIntent

# Module-level state machine singleton for current active device state
_global_state_machine = RobotStateMachine(
    initial_state=RobotState.IDLE,
    battery_level=98.0,
    has_obstacle=False,
)


def get_state_machine() -> RobotStateMachine:
    """Return the active robot state machine instance."""
    return _global_state_machine


class RobotService:
    """Service handling robot status, events, and state machine transitions."""

    @staticmethod
    async def get_status(
        db: Optional[AsyncSession] = None,
        device_id: str = "rover_01",
    ) -> Dict[str, Any]:
        """Retrieve current device status, state, battery, and telemetry summary."""
        sm = get_state_machine()

        status_data = {
            "device_id": device_id,
            "status": sm.state.value,
            "battery_level": sm.battery_level,
            "has_obstacle": sm.has_obstacle,
            "current_room_id": sm.current_room_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Attempt to pull database device record if session is active
        if db is not None:
            try:
                result = await db.execute(
                    select(Device).where(Device.id == device_id)
                )
                device = result.scalars().first()
                if device:
                    status_data["name"] = device.name
                    status_data["device_type"] = device.device_type
                    status_data["firmware_version"] = device.firmware_version
                    status_data["last_seen"] = (
                        device.last_seen.isoformat()
                        if device.last_seen
                        else None
                    )
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in RobotService.get_status: %s", e)
                else:
                    logger.error("Database query failure in RobotService.get_status: %s", e, exc_info=True)
                    raise

        return status_data

    @staticmethod
    async def execute_command(
        command: Command,
        db: Optional[AsyncSession] = None,
        device_id: str = "rover_01",
    ) -> Dict[str, Any]:
        """Execute a structured command against the state machine and log events.

        Args:
            command: Validated Command schema instance.
            db: Optional database session for persisting event log.
            device_id: Identifier of targeted rover device.

        Returns:
            Dictionary with resulting status and execution metadata.

        Raises:
            CommandRejectionError: If rejected by safety/priority rules.
        """
        sm = get_state_machine()
        new_state = sm.execute_command(command)

        # Log robot event to DB if available
        if db is not None:
            try:
                event = RobotEvent(
                    device_id=device_id,
                    event_type=f"COMMAND_{command.intent.value}",
                    payload={
                        "room_id": command.room_id,
                        "priority": command.priority,
                        "new_state": new_state.value,
                    },
                )
                db.add(event)
                await db.commit()
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in RobotService.execute_command: %s", e)
                else:
                    logger.error("Database persistence failure in RobotService.execute_command: %s", e, exc_info=True)
                    raise

        return {
            "command": command.intent.value,
            "room_id": command.room_id,
            "status": new_state.value,
            "battery_level": sm.battery_level,
            "has_obstacle": sm.has_obstacle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    async def list_events(
        db: Optional[AsyncSession] = None,
        device_id: str = "rover_01",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical robot events."""
        events: List[Dict[str, Any]] = []

        if db is not None:
            try:
                result = await db.execute(
                    select(RobotEvent)
                    .where(RobotEvent.device_id == device_id)
                    .order_by(desc(RobotEvent.timestamp))
                    .limit(limit)
                )
                records = result.scalars().all()
                for rec in records:
                    events.append({
                        "id": rec.id,
                        "device_id": rec.device_id,
                        "event_type": rec.event_type,
                        "payload": rec.payload,
                        "timestamp": rec.timestamp.isoformat(),
                    })
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in RobotService.list_events: %s", e)
                else:
                    logger.error("Database query failure in RobotService.list_events: %s", e, exc_info=True)
                    raise

        return events
