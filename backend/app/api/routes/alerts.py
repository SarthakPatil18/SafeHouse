"""Anomaly and caregiver alert notification API endpoints.

Per Section 5 and Section 7 of AGENTS.md:
- GET /api/alerts: list alerts, filterable by status and room.
- POST /api/alerts/{id}/acknowledge: marks alert status acknowledged and sets timestamp.
- GET /api/alerts/anomalies: list detected anomalies.
- All responses use the Section 7 envelope.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (e.g. active, acknowledged)"),
    room: Optional[str] = Query(None, description="Filter by room ID (e.g. room_1, room_3)"),
    room_id: Optional[str] = Query(None, description="Filter by room ID"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve alerts generated from confirmed environmental anomalies."""
    target_room = room_id or room
    alerts = await AlertService.list_alerts(status=status, room_id=target_room, db=db)
    return SuccessResponse(data=alerts)


@router.post("/{alert_id}/acknowledge")
@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an active alert notification."""
    result = await AlertService.acknowledge_alert(alert_id=alert_id, db=db)
    if not result:
        return ErrorResponse(
            error=ErrorDetail(code="ALERT_NOT_FOUND", message=f"Alert '{alert_id}' not found.")
        )
    return SuccessResponse(data=result)


@router.get("/anomalies", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_anomalies(
    room_id: Optional[str] = Query(None, description="Filter by room ID"),
    room: Optional[str] = Query(None, description="Filter by room ID"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve deterministic rule engine anomaly detection records."""
    target_room = room_id or room
    anomalies = await AlertService.list_anomalies(room_id=target_room, db=db)
    return SuccessResponse(data=anomalies)
