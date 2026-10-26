from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.database import database_checkup
from app.websocket import websocket_checkup


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await database_checkup()
    await websocket_checkup()
    yield


app = FastAPI(
    title="Mapa Colaborativo",
    description="Minicurso de Geoinformática: FastAPI + WebSocket + SpatiaLite",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.frontend("/", directory="public", fallback="index.html")
