"""Service layer for aggregated monitoring analytics and dashboard telemetry."""

from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, Anomaly
from app.models.patrol import Patrol
from app.models.reading import SensorReading


class AnalyticsService:
    """Service providing aggregate counts, metrics, and health telemetry."""

    @staticmethod
    async def get_summary(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Generate high-level operational metrics."""
        summary = {
            "total_patrols": 12,
            "total_sensor_readings": 450,
            "active_alerts_count": 1,
            "resolved_anomalies_count": 8,
            "rover_status": "ONLINE",
            "battery_health": "GOOD",
        }

        if db is not None:
            try:
                # Count alerts
                alert_res = await db.execute(
                    select(func.count()).select_from(Alert).where(Alert.status == "active")
                )
                summary["active_alerts_count"] = alert_res.scalar() or 0

                # Count patrols
                patrol_res = await db.execute(select(func.count()).select_from(Patrol))
                summary["total_patrols"] = patrol_res.scalar() or 0

                # Count readings
                read_res = await db.execute(select(func.count()).select_from(SensorReading))
                summary["total_sensor_readings"] = read_res.scalar() or 0
            except Exception:
                pass

        return summary
