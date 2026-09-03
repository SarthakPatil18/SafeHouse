"""SafeRoom FastAPI backend application entrypoint.

Per Section 7 of AGENTS.md:
- Structured logging (request path, latency, status code).
- Global exception handlers: All unhandled exceptions, validation errors, and 404s
  return the Section 7 error envelope shape consistently:
  { "success": false, "data": null, "error": { "code": "...", "message": "..." }, "timestamp": "..." }
- GET /health returns basic system status (db reachable, device connected count, uptime).
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.ai import router as ai_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.patrols import router as patrols_router
from app.api.routes.robot import router as robot_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.websocket import router as websocket_router
from app.core.config import settings
from app.core.db import check_db_health, init_db
from app.core.logging import StructuredLoggingMiddleware, logger
from app.schemas.responses import SuccessResponse
from app.services.device_manager import get_device_manager

STATIC_INDEX = Path(__file__).parent / "static" / "index.html"
START_TIME = datetime.now(timezone.utc)


def _mask_db_url(url: str) -> str:
    """Mask credentials in database connection string for diagnostic logging."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        user_pass, host_db = rest.split("@", 1)
        user = user_pass.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host_db}"
    return url


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    masked_db = _mask_db_url(settings.DATABASE_URL)
    logger.info(
        "SafeRoom backend starting up. ENVIRONMENT=%s, RESOLVED_DATABASE_URL=%s",
        settings.ENVIRONMENT,
        masked_db,
    )
    try:
        await init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning("Database initialization deferred / memory fallback: %s", e)
    yield
    logger.info("SafeRoom backend shutting down.")



app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. Structured Access Logging Middleware
app.add_middleware(StructuredLoggingMiddleware)

# 2. CORS Middleware for Dashboard Clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Global Section 7 Envelope Exception Handlers
# -------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Ensure Pydantic/FastAPI request validation errors conform to Section 7 error envelope."""
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_messages.append(f"{loc}: {msg}" if loc else msg)

    formatted_message = "; ".join(error_messages) if error_messages else "Request validation failed."

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": formatted_message,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Ensure direct Pydantic validation errors conform to Section 7 error envelope."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure FastAPI HTTP exceptions conform to Section 7 error envelope."""
    code = "HTTP_ERROR"
    message = str(exc.detail)
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", message)
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Ensure unrouted 404s and Starlette HTTP exceptions conform to Section 7 error envelope."""
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": str(exc.detail) if exc.detail else "HTTP Error",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler ensuring unhandled server exceptions conform to Section 7 envelope."""
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# -------------------------------------------------------------
# Include Application Routers
# -------------------------------------------------------------

api_prefix = settings.API_V1_STR  # default "/api"
app.include_router(robot_router, prefix=api_prefix)
app.include_router(rooms_router, prefix=api_prefix)
app.include_router(sensors_router, prefix=api_prefix)
app.include_router(patrols_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(ai_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(simulation_router, prefix=api_prefix)

# Include WebSocket router
app.include_router(websocket_router)
app.include_router(websocket_router, prefix=api_prefix)


# -------------------------------------------------------------
# Core Service Endpoints
# -------------------------------------------------------------

@app.get("/health", response_model=SuccessResponse[dict])
async def health_check():
    """Health check endpoint returning basic status (db reachable, device connected count, uptime)."""
    db_status = await check_db_health()
    connected_devices = get_device_manager().connected_count
    uptime_seconds = round((datetime.now(timezone.utc) - START_TIME).total_seconds(), 2)

    return SuccessResponse(
        data={
            "status": "healthy" if db_status else "degraded",
            "db_reachable": db_status,
            "device_connected_count": connected_devices,
            "uptime_seconds": uptime_seconds,
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Interactive simulation and rover control dashboard UI."""
    if STATIC_INDEX.exists():
        return HTMLResponse(content=STATIC_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>SafeRoom Simulation Dashboard</h1>")


@app.get("/", response_model=SuccessResponse[dict])
async def root(request: Request):
    """Root endpoint returning service identity or web UI for browser requests."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept and STATIC_INDEX.exists():
        return HTMLResponse(content=STATIC_INDEX.read_text(encoding="utf-8"))

    return SuccessResponse(
        data={
            "service": "SafeRoom Backend API",
            "docs": "/docs",
            "dashboard": "/dashboard",
            "version": "1.0.0",
        }
    )
