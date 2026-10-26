"""Backend do mapa colaborativo: FastAPI + WebSocket + SpatiaLite."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

import db

STATIC_DIR = db.BASE_DIR / "static"
TIPOS_ACEITOS = {"Point", "LineString", "Polygon"}


class FeatureIn(BaseModel):
    """GeoJSON Feature recebido pelo POST /api/features."""

    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)


class Conexoes:
    """Mantém os WebSockets ativos e envia mensagens para todos."""

    def __init__(self) -> None:
        self.ativas: set[WebSocket] = set()

    async def conectar(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.ativas.add(websocket)

    def desconectar(self, websocket: WebSocket) -> None:
        self.ativas.discard(websocket)

    async def broadcast(self, mensagem: dict[str, Any]) -> None:
        for websocket in list(self.ativas):
            try:
                await websocket.send_json(mensagem)
            except Exception:
                self.desconectar(websocket)


conexoes = Conexoes()


def validar_geometria(geometria: dict[str, Any]) -> str:
    """Valida o GeoJSON com Shapely e devolve o WKT para o banco."""
    try:
        geom: BaseGeometry = shape(geometria)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="GeoJSON de geometria inválido.",
        ) from exc

    if geom.is_empty:
        raise HTTPException(status_code=422, detail="A geometria está vazia.")

    if geom.geom_type not in TIPOS_ACEITOS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Tipo de geometria não aceito: {geom.geom_type}. "
                "Use Point, LineString ou Polygon."
            ),
        )

    if not geom.is_valid:
        raise HTTPException(
            status_code=422,
            detail=(
                "Geometria inválida (por exemplo, polígono com auto-interseção). "
                "Desenhe novamente."
            ),
        )

    return geom.wkt


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.verificar_banco()
    yield


app = FastAPI(
    title="Mapa Colaborativo",
    description="Minicurso de Geoinformática: FastAPI + WebSocket + SpatiaLite",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/features")
def listar_features() -> dict[str, Any]:
    """Retorna todas as geometrias como uma FeatureCollection GeoJSON."""
    return {"type": "FeatureCollection", "features": db.listar_features()}


@app.post("/api/features", status_code=201)
async def criar_feature(feature: FeatureIn) -> dict[str, Any]:
    """Valida, grava e avisa todos os clientes conectados."""
    wkt = validar_geometria(feature.geometry)
    nova = db.criar_feature(wkt)

    await conexoes.broadcast({"type": "feature_added", "feature": nova})
    return nova


@app.delete("/api/features/{feature_id}", status_code=204)
async def excluir_feature(feature_id: int) -> None:
    if not db.excluir_feature(feature_id):
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")

    await conexoes.broadcast({"type": "feature_removed", "id": feature_id})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await conexoes.conectar(websocket)

    try:
        # Ao entrar, o cliente recebe o estado atual do mapa.
        await websocket.send_json(
            {"type": "snapshot", "features": db.listar_features()}
        )

        # A partir daqui o canal é usado apenas pelo servidor para notificar
        # eventos. O receive mantém a conexão aberta.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        conexoes.desconectar(websocket)
    except Exception:
        conexoes.desconectar(websocket)
