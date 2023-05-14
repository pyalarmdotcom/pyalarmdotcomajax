"""Base device-specific websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.websockets.messages import WebSocketMessage

log = logging.getLogger(__name__)


class BaseWebSocketHandler:
    """Base class for device-type-specific websocket message handler."""

    def __init__(self) -> None:
        """Initialize handler."""

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""
        raise NotImplementedError
