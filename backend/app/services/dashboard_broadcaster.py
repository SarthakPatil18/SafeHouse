"""In-process connection manager and broadcaster for live browser dashboard WebSockets.

Per Section 2 of AGENTS.md:
- Browser transport uses WebSocket for live updates.
- Broadcasts messages in the shape: { "type": "sensor_update" | "alert", "data": {...} }
"""

from typing import Any, Dict, List, Set
from fastapi import WebSocket
from app.core.logging import logger


class DashboardConnectionManager:
    """Manages active browser dashboard WebSocket clients and broadcasts live events."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Register and accept a new browser dashboard connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            "Dashboard client connected. Active dashboard clients: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected dashboard client."""
        self.active_connections.discard(websocket)
        logger.info(
            "Dashboard client disconnected. Active dashboard clients: %d",
            len(self.active_connections),
        )

    async def broadcast(self, message_type: str, data: Dict[str, Any]) -> None:
        """Broadcast payload to all connected dashboard websockets.

        Payload shape: { "type": "sensor_update" | "alert", "data": {...} }
        """
        if not self.active_connections:
            return

        message = {
            "type": message_type,
            "data": data,
        }

        dead_connections: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug("Failed to broadcast to dashboard client: %s", e)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)

    def clear(self) -> None:
        """Clear all active connections (useful for resetting test state)."""
        self.active_connections.clear()


dashboard_manager = DashboardConnectionManager()


async def broadcast_sensor_update(reading_data: Dict[str, Any]) -> None:
    """Broadcast new sensor reading to all dashboard subscribers."""
    await dashboard_manager.broadcast("sensor_update", reading_data)


async def broadcast_alert(alert_data: Dict[str, Any]) -> None:
    """Broadcast new anomaly alert to all dashboard subscribers."""
    await dashboard_manager.broadcast("alert", alert_data)
