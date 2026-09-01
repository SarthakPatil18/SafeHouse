"""Service layer for sensor reading ingestion, storage, and anomaly evaluation."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Anomaly
from app.models.reading import SensorReading
from app.schemas.sensors import SensorReadingCreate
from app.services.anomaly_service import evaluate_reading_anomalies
from app.services.dashboard_broadcaster import broadcast_sensor_update
from app.services.room_service import DEFAULT_ROOMS

# In-memory buffer for recent readings
_recent_readings_buffer: List[Dict[str, Any]] = []


class SensorService:
    """Service handling environmental telemetry ingestion and history querying."""

    @staticmethod
    async def record_reading(
        reading_in: SensorReadingCreate,
        db: Optional[AsyncSession] = None,
        process_worker: bool = True,
    ) -> Dict[str, Any]:
        """Ingest a sensor reading, evaluate baselines for anomalies, and persist record."""
        reading_dict = reading_in.model_dump()
        reading_id = f"sr_{uuid.uuid4().hex[:8]}"
        reading_dict["id"] = reading_id

        if not reading_dict.get("timestamp"):
            reading_dict["timestamp"] = datetime.now(timezone.utc)

        # 1. Lookup Room Baseline
        room_id = reading_in.room_id
        baseline = None
        if room_id and room_id in DEFAULT_ROOMS:
            baseline = DEFAULT_ROOMS[room_id].get("baseline")

        # 2. Evaluate Deterministic Anomalies
        detected_anomalies: List[Dict[str, Any]] = []
        if baseline:
            raw_anomalies = evaluate_reading_anomalies(reading_dict, baseline)
            for a in raw_anomalies:
                anomaly_record = {
                    "id": f"anom_{uuid.uuid4().hex[:8]}",
                    "room_id": room_id,
                    "reading_id": reading_id,
                    "type": a["type"],
                    "severity": a["severity"],
                    "value": a["value"],
                    "expected_min": a["expected_min"],
                    "expected_max": a["expected_max"],
                    "status": "detected",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
                detected_anomalies.append(anomaly_record)

        # 3. Store in Memory
        reading_output = dict(reading_dict)
        if isinstance(reading_output["timestamp"], datetime):
            reading_output["timestamp"] = reading_output["timestamp"].isoformat()
        reading_output["anomalies"] = detected_anomalies
        _recent_readings_buffer.append(reading_output)

        # 4. Store in Database if available
        if db is not None:
            try:
                db_reading = SensorReading(
                    id=reading_id,
                    device_id=reading_in.device_id,
                    room_id=reading_in.room_id,
                    temperature=reading_in.temperature,
                    humidity=reading_in.humidity,
                    sound_level=reading_in.sound_level,
                    battery=reading_in.battery,
                    timestamp=reading_dict["timestamp"],
                )
                db.add(db_reading)

                for anom in detected_anomalies:
                    db_anomaly = Anomaly(
                        id=anom["id"],
                        room_id=anom["room_id"],
                        reading_id=anom["reading_id"],
                        type=anom["type"],
                        severity=anom["severity"],
                        value=anom["value"],
                        expected_min=anom["expected_min"],
                        expected_max=anom["expected_max"],
                        status=anom["status"],
                        detected_at=datetime.now(timezone.utc),
                    )
                    db.add(db_anomaly)

                await db.commit()
            except Exception:
                pass

        # 5. Broadcast live update to all active browser dashboard WebSocket clients
        await broadcast_sensor_update(reading_output)

        # 6. Process through AnomalyWorker pipeline (recheck + alert broadcast) if enabled
        if process_worker:
            from app.workers.anomaly_worker import AnomalyWorker
            worker_res = await AnomalyWorker.process_reading(reading_output, db=db)
            reading_output["worker_action"] = worker_res.get("action")

        return reading_output

    @staticmethod
    async def get_latest_reading(
        device_id: str = "rover_01",
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent sensor reading."""
        if db is not None:
            try:
                result = await db.execute(
                    select(SensorReading)
                    .where(SensorReading.device_id == device_id)
                    .order_by(desc(SensorReading.timestamp))
                    .limit(1)
                )
                rec = result.scalars().first()
                if rec:
                    return {
                        "id": rec.id,
                        "device_id": rec.device_id,
                        "room_id": rec.room_id,
                        "temperature": rec.temperature,
                        "humidity": rec.humidity,
                        "sound_level": rec.sound_level,
                        "battery": rec.battery,
                        "timestamp": rec.timestamp.isoformat(),
                    }
            except Exception:
                pass

        if _recent_readings_buffer:
            return _recent_readings_buffer[-1]

        # Default fallback sample
        return {
            "id": "sr_sample",
            "device_id": device_id,
            "room_id": "room_1",
            "temperature": 21.0,
            "humidity": 45.0,
            "sound_level": 32.0,
            "battery": 98.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    async def get_history(
        room_id: Optional[str] = None,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical sensor readings."""
        if db is not None:
            try:
                stmt = select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(limit)
                if room_id:
                    stmt = stmt.where(SensorReading.room_id == room_id)
                result = await db.execute(stmt)
                records = result.scalars().all()
                if records:
                    return [
                        {
                            "id": r.id,
                            "device_id": r.device_id,
                            "room_id": r.room_id,
                            "temperature": r.temperature,
                            "humidity": r.humidity,
                            "sound_level": r.sound_level,
                            "battery": r.battery,
                            "timestamp": r.timestamp.isoformat(),
                        }
                        for r in records
                    ]
            except Exception:
                pass

        # In-memory buffer fallback
        filtered = _recent_readings_buffer
        if room_id:
            filtered = [r for r in filtered if r.get("room_id") == room_id]
        return list(reversed(filtered[-limit:]))
