"""Manager for active hardware ESP32 rover WebSocket connections to dispatch commands."""

from typing import Any, Dict, Optional
from fastapi import WebSocket
from app.core.logging import logger


class DeviceConnectionManager:
    """Registry of connected hardware rover WebSockets to send downstream commands."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._dispatched_commands: Dict[str, list] = {}

    @property
    def connected_count(self) -> int:
        """Return the count of currently active device WebSocket connections."""
        return len(self._connections)

    def register(self, device_id: str, websocket: WebSocket) -> None:
        """Register an active ESP32 rover WebSocket connection."""
        self._connections[device_id] = websocket
        if device_id not in self._dispatched_commands:
            self._dispatched_commands[device_id] = []
        logger.info("Registered active hardware connection for device '%s'.", device_id)


    def unregister(self, device_id: str) -> None:
        """Unregister a disconnected rover WebSocket."""
        self._connections.pop(device_id, None)
        logger.info("Unregistered hardware connection for device '%s'.", device_id)

    async def send_command(self, device_id: str, command_dict: Dict[str, Any]) -> bool:
        """Send a structured command payload over WebSocket to the physical rover.

        Args:
            device_id: Target rover device ID.
            command_dict: Command object dictionary (intent, room_id, priority).

        Returns:
            True if sent over active socket, False if device not connected.
        """
        # Keep track of dispatched commands for telemetry and testing
        if device_id not in self._dispatched_commands:
            self._dispatched_commands[device_id] = []
        self._dispatched_commands[device_id].append(command_dict)

        ws = self._connections.get(device_id)
        if ws is not None:
            try:
                await ws.send_json(command_dict)
                logger.info("Dispatched command %s to device '%s'.", command_dict.get("intent"), device_id)
                return True
            except Exception as e:
                logger.warning("Failed sending command to device '%s': %s", device_id, e)
                return False

        logger.debug("Device '%s' not actively connected via WebSocket; command logged.", device_id)
        return False

    def get_dispatched_commands(self, device_id: str = "rover_01") -> list:
        """Retrieve historical dispatched commands for a device (useful in tests)."""
        return self._dispatched_commands.get(device_id, [])

    def clear(self) -> None:
        """Reset connection and dispatch history."""
        self._connections.clear()
        self._dispatched_commands.clear()


device_manager = DeviceConnectionManager()


def get_device_manager() -> DeviceConnectionManager:
    """Return the singleton device connection manager."""
    return device_manager
