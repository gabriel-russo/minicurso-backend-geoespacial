from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, WebSocket, WebSocketDisconnect, WebSocketException


class WebSocketManager:
    """
    Gerenciador de WebSocket

    https://fastapi.tiangolo.com/advanced/websockets/?h=websock#handling-disconnections-and-multiple-clients
    """

    def __init__(self) -> None:
        self.__active_conections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.__active_conections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.__active_conections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for websocket in list(self.__active_conections):
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, WebSocketException, RuntimeError):
                self.disconnect(websocket)


_ws_manager: WebSocketManager | None = None


async def websocket_checkup() -> None:
    global _ws_manager

    if _ws_manager is None:
        _ws_manager = WebSocketManager()


async def acquire_websocket() -> AsyncGenerator[WebSocketManager]:
    global _ws_manager

    if _ws_manager is None:
        raise HTTPException(status_code=500, detail="WebSocket not connected")

    yield _ws_manager
