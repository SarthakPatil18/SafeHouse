"""Service layer for aggregated monitoring analytics and dashboard telemetry."""

from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import is_db_connection_error
from app.core.logging import logger
from app.models.alert import Alert, Anomaly
from app.models.patrol import Patrol
from app.models.reading import SensorReading
from app.services.robot_service import get_state_machine


class AnalyticsService:
    """Service providing real aggregate counts, metrics, and health telemetry."""

    @staticmethod
    async def get_summary(db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Generate high-level operational metrics from live database queries."""
        sm = get_state_machine()
        battery_lvl = sm.battery_level
        battery_health = "GOOD" if battery_lvl >= 50.0 else ("FAIR" if battery_lvl >= 20.0 else "LOW")

        summary: Dict[str, Any] = {
            "total_patrols": 0,
            "total_sensor_readings": 0,
            "active_alerts_count": 0,
            "resolved_anomalies_count": 0,
            "rover_status": sm.state.value,
            "battery_health": battery_health,
        }

        if db is not None:
            try:
                # Count active alerts
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

                # Count resolved anomalies
                anom_res = await db.execute(
                    select(func.count()).select_from(Anomaly).where(Anomaly.status == "RESOLVED")
                )
                summary["resolved_anomalies_count"] = anom_res.scalar() or 0
            except Exception as e:
                if is_db_connection_error(e):
                    logger.warning("Database connection unavailable in AnalyticsService.get_summary: %s", e)
                else:
                    logger.error("Database query failure in AnalyticsService.get_summary: %s", e, exc_info=True)
                    raise

        return summary
