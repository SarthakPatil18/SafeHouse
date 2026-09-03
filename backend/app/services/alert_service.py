"""Service layer for anomaly review and caregiver alerts."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import is_db_connection_error
from app.core.logging import logger
from app.models.alert import Alert, Anomaly

# In-memory store for alerts (starts empty - no fake demo data)
_alerts_store: List[Dict[str, Any]] = []


class AlertService:
    """Service managing anomaly notifications and caregiver alerts."""

    @staticmethod
    async def list_alerts(
        status: Optional[str] = None,
        room_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """List alerts with optional status and room_id filters."""
        if db is not None:
            try:
                stmt = select(Alert).order_by(desc(Alert.created_at))
                if status:
                    stmt = stmt.where(Alert.status == status)
                if room_id:
                    stmt = stmt.where(Alert.room_id == room_id)
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
                return []
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in AlertService.list_alerts: %s", e)
                else:
                    logger.error("Database query failure in AlertService.list_alerts: %s", e, exc_info=True)
                    raise

        # In-memory store fallback (active alerts created by AnomalyWorker)
        all_in_memory = list(_alerts_store)
        from app.workers.anomaly_worker import get_created_alerts
        for wa in get_created_alerts():
            if not any(a["id"] == wa["id"] for a in all_in_memory):
                all_in_memory.append(wa)

        filtered = all_in_memory
        if status:
            filtered = [a for a in filtered if a.get("status") == status]
        if room_id:
            filtered = [a for a in filtered if a.get("room_id") == room_id]
        return filtered

    @staticmethod
    async def acknowledge_alert(
        alert_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark an active alert as acknowledged."""
        now_str = datetime.now(timezone.utc).isoformat()
        now_dt = datetime.now(timezone.utc)

        target = None
        for a in _alerts_store:
            if a["id"] == alert_id:
                a["status"] = "acknowledged"
                a["acknowledged_at"] = now_str
                target = a
                break

        from app.workers.anomaly_worker import get_created_alerts
        for a in get_created_alerts():
            if a["id"] == alert_id:
                a["status"] = "acknowledged"
                a["acknowledged_at"] = now_str
                if target is None:
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
                    db_alert.acknowledged_at = now_dt
                    await db.commit()
                    return {
                        "id": db_alert.id,
                        "anomaly_id": db_alert.anomaly_id,
                        "room_id": db_alert.room_id,
                        "severity": db_alert.severity,
                        "message": db_alert.message,
                        "channel": db_alert.channel,
                        "status": db_alert.status,
                        "created_at": (
                            db_alert.created_at.isoformat()
                            if isinstance(db_alert.created_at, datetime)
                            else str(db_alert.created_at)
                        ),
                        "acknowledged_at": (
                            db_alert.acknowledged_at.isoformat()
                            if isinstance(db_alert.acknowledged_at, datetime)
                            else str(db_alert.acknowledged_at)
                        ),
                    }
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in AlertService.acknowledge_alert: %s", e)
                else:
                    logger.error("Database query failure in AlertService.acknowledge_alert: %s", e, exc_info=True)
                    raise

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
                return []
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in AlertService.list_anomalies: %s", e)
                else:
                    logger.error("Database query failure in AlertService.list_anomalies: %s", e, exc_info=True)
                    raise

        return []
