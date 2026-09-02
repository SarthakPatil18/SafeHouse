"""Security and authentication utilities for device access.

Per AGENTS.md Section 8 and Prompt specifications:
- Single device token authentication for hackathon MVP.
- Verifies token against settings.DEVICE_TOKEN.
- Enforced on:
  1. Hardware WebSocket connection (/ws/device/{device_id}) -> closes connection if invalid/missing.
  2. Sensor ingestion REST endpoints (/api/sensors/readings) -> rejects with 401 UNAUTHORIZED.
- Out of scope: User auth, Supabase Auth, JWT.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# HTTP Bearer security scheme for Swagger / OpenAPI docs
security_bearer = HTTPBearer(auto_error=False)


def verify_device_token(token: Optional[str]) -> bool:
    """Verify incoming device authentication token against configured DEVICE_TOKEN.

    If DEVICE_TOKEN is set in settings, incoming token must match exactly.
    If DEVICE_TOKEN is unset or empty, verification passes in development.
    """
    configured = settings.DEVICE_TOKEN.strip() if settings.DEVICE_TOKEN else ""
    if not configured:
        return True

    if not token:
        return False

    return token.strip() == configured


async def validate_device_token(
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    token_query: Optional[str] = Query(None, alias="token"),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> bool:
    """FastAPI dependency to enforce device token authentication on sensor ingestion routes.

    Extracts token from:
    1. 'X-Device-Token' header
    2. 'Authorization: Bearer <token>' header
    3. '?token=<token>' query parameter

    Raises HTTPException (401 UNAUTHORIZED) if token is invalid or missing.
    """
    token = (
        x_device_token
        or (bearer_auth.credentials if bearer_auth else None)
        or token_query
    )

    if not verify_device_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing device authentication token.",
            },
        )
    return True
