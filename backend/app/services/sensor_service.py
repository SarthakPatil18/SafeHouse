"""Service layer for sensor reading ingestion, storage, and anomaly evaluation."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Anomaly
from app.models.reading import SensorReading
from app.schemas.sensors import SensorReadingCreate
from app.services.anomaly_service import detect_gas_anomaly, detect_motion_anomaly
from app.services.dashboard_broadcaster import broadcast_sensor_update
from app.services.room_service import DEFAULT_ROOMS

# In-memory buffer for recent readings
_recent_readings_buffer: List[Dict[str, Any]] = []


class SensorService:
    """Service handling environmental telemetry ingestion and history querying."""

    @staticmethod
    async def get_last_motion_timestamp(
        room_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[datetime]:
        """Fetch last_motion_at by querying the most recent sensor_readings row for that room where pir_motion=True."""
        if db is not None:
            try:
                stmt = (
                    select(SensorReading.timestamp)
                    .where(SensorReading.room_id == room_id, SensorReading.pir_motion == True)
                    .order_by(desc(SensorReading.timestamp))
                    .limit(1)
                )
                result = await db.execute(stmt)
                ts = result.scalar_one_or_none()
                if ts:
                    return ts
            except Exception:
                pass

        # In-memory buffer fallback
        for r in reversed(_recent_readings_buffer):
            if r.get("room_id") == room_id and (r.get("pir_motion") is True or r.get("pir_motion") == 1):
                ts = r.get("timestamp")
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        pass
                elif isinstance(ts, datetime):
                    return ts
        return None

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

        # 2. Fetch last_motion_at for motion anomaly detection
        last_motion_at = None
        if room_id:
            last_motion_at = await SensorService.get_last_motion_timestamp(room_id, db=db)

        # 3. Evaluate Deterministic Gas and Motion Anomalies Separately
        detected_anomalies: List[Dict[str, Any]] = []
        if baseline:
            gas_anoms = detect_gas_anomaly(reading_dict, baseline)
            motion_anom = detect_motion_anomaly(reading_dict, baseline, last_motion_at=last_motion_at)

            raw_anomalies = list(gas_anoms)
            if motion_anom is not None:
                raw_anomalies.append(motion_anom)

            for a in raw_anomalies:
                anomaly_record = {
                    "id": f"anom_{uuid.uuid4().hex[:8]}",
                    "room_id": room_id,
                    "reading_id": reading_id,
                    "type": a["type"],
                    "severity": a["severity"],
                    "value": a["value"],
                    "expected_min": a.get("expected_min"),
                    "expected_max": a.get("expected_max"),
                    "status": "detected",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
                detected_anomalies.append(anomaly_record)


        # 3. Store in Memory
        reading_output = dict(reading_dict)
        if isinstance(reading_output["timestamp"], datetime):
            reading_output["timestamp"] = reading_output["timestamp"].isoformat()
        reading_output["source"] = reading_dict.get("source", "live")
        reading_output["anomalies"] = detected_anomalies
        _recent_readings_buffer.append(reading_output)

        # 4. Store in Database if available
        if db is not None:
            try:
                db_reading = SensorReading(
                    id=reading_id,
                    device_id=reading_in.device_id,
                    room_id=reading_in.room_id,
                    pir_motion=reading_in.pir_motion,
                    gas_mq135=reading_in.gas_mq135,
                    gas_mq2=reading_in.gas_mq2,
                    ultrasonic_distance_cm=reading_in.ultrasonic_distance_cm,
                    battery=reading_in.battery,
                    timestamp=reading_dict["timestamp"],
                    source=reading_dict.get("source", "live"),
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
                        "pir_motion": rec.pir_motion,
                        "gas_mq135": rec.gas_mq135,
                        "gas_mq2": rec.gas_mq2,
                        "ultrasonic_distance_cm": rec.ultrasonic_distance_cm,
                        "battery": rec.battery,
                        "source": rec.source,
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
            "pir_motion": False,
            "gas_mq135": 25.0,
            "gas_mq2": 15.0,
            "ultrasonic_distance_cm": 120.0,
            "battery": 98.0,
            "source": "live",
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
                            "pir_motion": r.pir_motion,
                            "gas_mq135": r.gas_mq135,
                            "gas_mq2": r.gas_mq2,
                            "ultrasonic_distance_cm": r.ultrasonic_distance_cm,
                            "battery": r.battery,
                            "source": r.source,
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

