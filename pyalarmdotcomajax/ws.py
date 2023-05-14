"""Functions for communicating with Alarm.com over WebSockets."""
from __future__ import annotations

import logging

import aiohttp
from aiohttp import ClientSession

from . import const as c
from .errors import AuthenticationFailed, DataFetchFailed

log = logging.getLogger(__name__)


class WebSocketClient:
    """Class for communicating with Alarm.com over WebSockets."""

    WEBSOCKET_ENDPOINT_TEMPLATE = "wss://webskt.alarm.com:8443/?auth={}"
    WEBSOCKET_TOKEN_REQUEST_TEMPLATE = "{}web/api/websockets/token"  # noqa: S105

    def __init__(self, websession: ClientSession, ajax_headers: dict) -> None:
        """Initialize."""
        self._websession: ClientSession = websession
        self._ajax_headers: dict = ajax_headers

        self._ws_auth_token: str | None = None

    async def async_connect(self) -> None:
        """Connect to Alarm.com WebSocket."""

        # Get authentication token for websocket communication
        try:
            self._ws_auth_token = await self._async_get_websocket_token()
            if not self._ws_auth_token:
                raise AuthenticationFailed("async_connect(): Failed to get WebSocket authentication token.")
        except (DataFetchFailed, AuthenticationFailed) as err:
            raise AuthenticationFailed from err

        # Connect to websocket endpoint
        async with self._websession.ws_connect(
            self.WEBSOCKET_TOKEN_REQUEST_TEMPLATE.format(self._ws_auth_token),
            headers=self._ajax_headers,
        ) as websocket:
            async for msg in websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == "close cmd":
                        await websocket.close()
                        break
                    else:
                        await websocket.send_str(msg.data + "/answer")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

    async def _async_get_websocket_token(self) -> str:
        """Get authentication token for websocket communication."""
        async with self._websession.get(
            url=self.WEBSOCKET_TOKEN_REQUEST_TEMPLATE.format(c.URL_BASE, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await resp.json()

        if (
            ((errors := json_rsp.get("errors")) and len(errors) > 0)
            or ((validation_errors := json_rsp.get("validation_errors")) and len(validation_errors) > 0)
            or ((processing_errors := json_rsp.get("processingErrors")) and len(processing_errors) > 0)
            or ((token_value := json_rsp.get("value")) in [None, ""])
        ):
            log.debug(
                (
                    "async_get_websocket_token(): Received errors while requesting"
                    " WebSocket authentication token. Response: %s"
                ),
                resp,
            )
            raise DataFetchFailed(
                "async_get_websocket_token(): Received errors while requesting WebSocket authentication token."
            )

        return str(token_value)
