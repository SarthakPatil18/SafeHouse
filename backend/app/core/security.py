"""Security and authentication utilities for device and user access."""

from typing import Optional
from app.core.config import settings


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
