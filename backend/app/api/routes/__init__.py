"""API routes package initialization."""

from app.api.routes.ai import router as ai_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.patrols import router as patrols_router
from app.api.routes.robot import router as robot_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.websocket import router as websocket_router

__all__ = [
    "robot_router",
    "rooms_router",
    "sensors_router",
    "patrols_router",
    "alerts_router",
    "ai_router",
    "analytics_router",
    "websocket_router",
]
