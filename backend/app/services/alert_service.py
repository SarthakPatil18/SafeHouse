"""Service layer for anomaly review and caregiver alerts."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, Anomaly

# In-memory store for alerts
_alerts_store: List[Dict[str, Any]] = [
    {
        "id": "alert_demo_1",
        "anomaly_id": "anom_sample_1",
        "room_id": "room_3",
        "severity": "HIGH",
        "message": "Temperature in Guest Bedroom dropped to 14.5°C, below safe baseline (18.0°C).",
        "channel": "dashboard",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged_at": None,
    }
]


class AlertService:
    """Service managing anomaly notifications and caregiver alerts."""

    @staticmethod
    async def list_alerts(
        status: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """List alerts with optional status filter."""
        if db is not None:
            try:
                stmt = select(Alert).order_by(desc(Alert.created_at))
                if status:
                    stmt = stmt.where(Alert.status == status)
                result = await db.execute(stmt)
                records = result.scalars().all()
                if records:
                    return [
                        {
                            "id": a.id,
                            "anomaly_id": a.anomaly_id,
                            "room_id": a.room_id,
                            "severity": a.severity,
                            "message": a.message,
                            "channel": a.channel,
                            "status": a.status,
                            "created_at": a.created_at.isoformat(),
                            "acknowledged_at": (
                                a.acknowledged_at.isoformat()
                                if a.acknowledged_at
                                else None
                            ),
                        }
                        for a in records
                    ]
            except Exception:
                pass

        if status:
            return [a for a in _alerts_store if a.get("status") == status]
        return _alerts_store

    @staticmethod
    async def acknowledge_alert(
        alert_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark an active alert as acknowledged."""
        now = datetime.now(timezone.utc).isoformat()

        # Update in-memory
        target = None
        for a in _alerts_store:
            if a["id"] == alert_id:
                a["status"] = "acknowledged"
                a["acknowledged_at"] = now
                target = a
                break

        if db is not None:
            try:
                result = await db.execute(
                    select(Alert).where(Alert.id == alert_id)
                )
                db_alert = result.scalars().first()
                if db_alert:
                    db_alert.status = "acknowledged"
                    db_alert.acknowledged_at = datetime.now(timezone.utc)
                    await db.commit()
                    return {
                        "id": db_alert.id,
                        "anomaly_id": db_alert.anomaly_id,
                        "room_id": db_alert.room_id,
                        "severity": db_alert.severity,
                        "message": db_alert.message,
                        "channel": db_alert.channel,
                        "status": db_alert.status,
                        "created_at": db_alert.created_at.isoformat(),
                        "acknowledged_at": db_alert.acknowledged_at.isoformat(),
                    }
            except Exception:
                pass

        return target

    @staticmethod
    async def list_anomalies(
        room_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """List detected environmental anomalies."""
        if db is not None:
            try:
                stmt = select(Anomaly).order_by(desc(Anomaly.detected_at))
                if room_id:
                    stmt = stmt.where(Anomaly.room_id == room_id)
                result = await db.execute(stmt)
                records = result.scalars().all()
                if records:
                    return [
                        {
                            "id": an.id,
                            "room_id": an.room_id,
                            "reading_id": an.reading_id,
                            "type": an.type,
                            "severity": an.severity,
                            "value": an.value,
                            "expected_min": an.expected_min,
                            "expected_max": an.expected_max,
                            "status": an.status,
                            "detected_at": an.detected_at.isoformat(),
                            "resolved_at": (
                                an.resolved_at.isoformat()
                                if an.resolved_at
                                else None
                            ),
                        }
                        for an in records
                    ]
            except Exception:
                pass

        return []
