"""Hardware and browser WebSocket transport routes.

Per Section 2 and Section 5 of AGENTS.md:
1. Device WebSocket (/ws/device/{device_id}): ESP32 rover connection, authentication,
   and bidirectional telemetry/command streaming.
2. Dashboard WebSocket (/ws/dashboard): Browser dashboard client live event broadcasts
   in the shape: { "type": "sensor_update" | "alert", "data": {...} }
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_factory, get_db
from app.core.logging import logger
from app.core.security import verify_device_token
from app.models.device import Device, RobotEvent
from app.schemas.sensors import SensorReadingCreate
from app.services.anomaly_service import detect_gas_anomaly, detect_motion_anomaly
from app.services.dashboard_broadcaster import dashboard_manager
from app.services.device_manager import get_device_manager
from app.services.robot_service import get_state_machine
from app.services.room_service import DEFAULT_ROOMS
from app.services.sensor_service import SensorService

router = APIRouter(tags=["WebSockets"])



async def _log_device_event(
    device_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    new_status: Optional[str] = None,
    battery: Optional[float] = None,
) -> None:
    """Helper to log connection/operational events to DB and update device status."""
    now = datetime.now(timezone.utc)
    try:
        async with async_session_factory() as session:
            # 1. Log robot event
            event = RobotEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                device_id=device_id,
                event_type=event_type,
                payload=payload,
                timestamp=now,
            )
            session.add(event)

            # 2. Update or create device record
            result = await session.execute(
                select(Device).where(Device.id == device_id)
            )
            device = result.scalars().first()
            if device:
                if new_status:
                    device.status = new_status
                device.last_seen = now
                if battery is not None:
                    device.battery_level = battery
            else:
                device = Device(
                    id=device_id,
                    name=f"Rover {device_id}",
                    device_type="rover",
                    status=new_status or "IDLE",
                    battery_level=battery if battery is not None else 100.0,
                    last_seen=now,
                )
                session.add(device)

            await session.commit()
    except Exception as e:
        logger.debug("Database event logging deferred (%s).", e)


@router.websocket("/ws/dashboard")
async def dashboard_websocket_endpoint(websocket: WebSocket):
    """Browser-facing WebSocket endpoint for live dashboard telemetry and alert streaming."""
    await dashboard_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        dashboard_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("Dashboard WebSocket disconnected: %s", e)
        dashboard_manager.disconnect(websocket)


@router.websocket("/ws/device/{device_id}")
async def device_websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    token: Optional[str] = Query(None),
):
    """Hardware WebSocket endpoint for ESP32 rover connection and sensor stream."""
    # 1. Device Authentication
    client_token = (
        token
        or websocket.headers.get("x-device-token")
        or websocket.headers.get("authorization", "").replace("Bearer ", "")
    )

    if not verify_device_token(client_token):
        logger.warning(
            "Rejected WebSocket connection for device '%s': Invalid or missing token.",
            device_id,
        )
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or missing device token.",
        )
        return

    # 2. On Connect
    await websocket.accept()
    sm = get_state_machine()
    sm.set_online()
    get_device_manager().register(device_id, websocket)
    logger.info("ESP32 Device '%s' connected successfully via WebSocket.", device_id)

    client_ip = websocket.client.host if websocket.client else None
    await _log_device_event(
        device_id=device_id,
        event_type="CONNECTED",
        payload={"client_ip": client_ip},
        new_status="IDLE",
    )

    # 3. Telemetry Ingestion Loop
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError as e:
                await websocket.send_json({
                    "success": False,
                    "error": {"code": "INVALID_JSON", "message": str(e)},
                })
                continue

            if "device_id" not in payload:
                payload["device_id"] = device_id

            try:
                reading_in = SensorReadingCreate(**payload)
            except ValidationError as e:
                await websocket.send_json({
                    "success": False,
                    "error": {"code": "VALIDATION_ERROR", "message": str(e)},
                })
                continue

            # Query last_motion_at and evaluate gas and motion anomalies separately
            room_id = reading_in.room_id
            baseline = DEFAULT_ROOMS[room_id].get("baseline") if room_id in DEFAULT_ROOMS else None
            last_motion_at = await SensorService.get_last_motion_timestamp(room_id) if room_id else None

            if baseline:
                gas_anomalies = detect_gas_anomaly(reading_in, baseline)
                motion_anomaly = detect_motion_anomaly(reading_in, baseline, last_motion_at=last_motion_at)
            else:
                gas_anomalies = []
                motion_anomaly = None

            # Ingest, detect anomalies, save reading, and process recheck worker
            saved_reading = await SensorService.record_reading(reading_in, process_worker=True)

            # Update state machine battery
            sm.set_battery_level(reading_in.battery)

            anomalies = saved_reading.get("anomalies", [])
            is_anomaly = len(anomalies) > 0
            anomaly_types = [a["type"] for a in anomalies]

            # Acknowledge receipt to ESP32
            await websocket.send_json({
                "status": "acknowledged",
                "reading_id": saved_reading.get("id"),
                "is_anomaly": is_anomaly,
                "anomalies": anomaly_types,
                "worker_action": saved_reading.get("worker_action"),
                "robot_state": sm.state.value,
                "timestamp": saved_reading.get("timestamp"),
            })


    except WebSocketDisconnect:
        logger.info("ESP32 Device '%s' disconnected from WebSocket.", device_id)
        get_device_manager().unregister(device_id)
        sm.set_offline()
        await _log_device_event(
            device_id=device_id,
            event_type="DISCONNECTED",
            new_status="OFFLINE",
        )
    except Exception as e:
        logger.error("Unexpected error in device WebSocket for '%s': %s", device_id, e)
        get_device_manager().unregister(device_id)
        sm.set_offline()
        await _log_device_event(
            device_id=device_id,
            event_type="DISCONNECTED",
            payload={"error": str(e)},
            new_status="OFFLINE",
        )
