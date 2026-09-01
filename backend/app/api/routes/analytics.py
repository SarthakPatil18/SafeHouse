"""Analytics and operational metrics API endpoints."""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.responses import SuccessResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=SuccessResponse[Dict[str, Any]])
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """Retrieve aggregated operational metrics for the caregiver dashboard."""
    summary = await AnalyticsService.get_summary(db=db)
    return SuccessResponse(data=summary)
