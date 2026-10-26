from typing import Annotated

from aiosqlite import Connection
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.database import acquire_connection
from app.utils import row_to_feature
from app.websocket import WebSocketManager, acquire_websocket

router = APIRouter()


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: Annotated[WebSocketManager, Depends(acquire_websocket)],
    connection: Annotated[Connection, Depends(acquire_connection)],
) -> None:

    await ws_manager.connect(websocket)

    try:
        # Ao entrar, o cliente recebe o estado atual do mapa.
        async with connection.cursor() as cursor:
            await cursor.execute("""
                SELECT 
                    id, 
                    criado_por,
                    criado_em, 
                    AsGeoJSON(geom) AS geom
                FROM desenho
            """)

            await websocket.send_json(
                {
                    "message": "SNAPSHOT",
                    "payload": [row_to_feature(row) async for row in cursor],
                }
            )

        # A partir daqui o canal é usado apenas pelo servidor para notificar
        # eventos. O receive mantém a conexão aberta.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
