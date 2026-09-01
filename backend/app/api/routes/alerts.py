"""Anomaly and caregiver alert notification API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=SuccessResponse[List[Dict[str, Any]]])
async def list_alerts(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve alerts generated from confirmed environmental anomalies."""
    alerts = await AlertService.list_alerts(status=status, db=db)
    return SuccessResponse(data=alerts)


@router.post("/{alert_id}/acknowledge")
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
    room_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve deterministic rule engine anomaly detection records."""
    anomalies = await AlertService.list_anomalies(room_id=room_id, db=db)
    return SuccessResponse(data=anomalies)
