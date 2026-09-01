"""SafeRoom FastAPI backend application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.ai import router as ai_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.patrols import router as patrols_router
from app.api.routes.robot import router as robot_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.websocket import router as websocket_router
from app.core.config import settings
from app.core.logging import logger
from app.schemas.responses import SuccessResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("SafeRoom backend starting up in environment: %s", settings.ENVIRONMENT)
    yield
    logger.info("SafeRoom backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api
api_prefix = settings.API_V1_STR  # default "/api"
app.include_router(robot_router, prefix=api_prefix)
app.include_router(rooms_router, prefix=api_prefix)
app.include_router(sensors_router, prefix=api_prefix)
app.include_router(patrols_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(ai_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)

# Include WebSocket router
app.include_router(websocket_router)
app.include_router(websocket_router, prefix=api_prefix)


@app.get("/health", response_model=SuccessResponse[dict])
async def health_check():
    """Health check endpoint returning API envelope."""
    return SuccessResponse(
        data={
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }
    )


@app.get("/", response_model=SuccessResponse[dict])
async def root():
    """Root endpoint returning service identity."""
    return SuccessResponse(
        data={
            "service": "SafeRoom Backend API",
            "docs": "/docs",
            "version": "1.0.0",
        }
    )
