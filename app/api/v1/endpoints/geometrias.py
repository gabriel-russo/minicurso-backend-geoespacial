from typing import Annotated

from aiosqlite import Connection
from fastapi import APIRouter, HTTPException, status
from fastapi.params import Body, Depends
from shapely.geometry import shape
from shapely.wkt import dumps as as_wkt

from app.database import acquire_connection
from app.utils import row_to_feature, valid_geometry
from app.websocket import WebSocketManager, acquire_websocket

router = APIRouter()


@router.get("")
async def listar_features(conn: Annotated[Connection, Depends(acquire_connection)]):
    """
    Retorna todas as geometrias como uma FeatureCollection GeoJSON.
    """

    rows = await conn.execute(
        """
        SELECT 
            id, 
            criado_por,
            criado_em, 
            AsGeoJSON(geom) AS geom
        FROM desenho
        ORDER BY id;
        """
    )

    return [
        {
            "type": "FeatureCollection",
            "features": [row_to_feature(row) async for row in rows],
        }
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_feature(
    conn: Annotated[Connection, Depends(acquire_connection)],
    ws_manager: Annotated[WebSocketManager, Depends(acquire_websocket)],
    feature: Annotated[dict, Body()],
    user: str | None = None,
):
    """
    Valida, grava e avisa todos os clientes conectados.
    """
    if feature.get("geometry") is None or not valid_geometry(feature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Geometria inválida."
        )

    feat = shape(feature)

    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO desenho (criado_por, geom) VALUES (?, GeomFromText(?, 4326)) RETURNING id, criado_por, criado_em, AsGeoJSON(geom) AS geom",
            (user if user is not None else "Anon", as_wkt(feat)),
        )

        row = await cur.fetchone()

        await conn.commit()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geometria criada, mas não foi possível carregá-la.",
        )

    await ws_manager.broadcast({"message": "CREATE", "payload": row_to_feature(row)})

    return row_to_feature(row)


@router.delete("/{id_geometria}", status_code=status.HTTP_200_OK)
async def excluir_feature(
    id_geometria: int,
    conn: Annotated[Connection, Depends(acquire_connection)],
    ws_manager: Annotated[WebSocketManager, Depends(acquire_websocket)],
) -> None:

    async with conn.cursor() as cur:
        await cur.execute("SELECT 1 FROM desenho WHERE id = ?", (id_geometria,))
        q = await cur.fetchone()

        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM desenho WHERE id = ?", (id_geometria,))

        await conn.commit()

    await ws_manager.broadcast({"message": "DELETE", "payload": id_geometria})
