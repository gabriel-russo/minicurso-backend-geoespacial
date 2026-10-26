from fastapi import APIRouter

from .endpoints import geometrias, websocket

router = APIRouter()

router.include_router(geometrias.router, prefix="/geometrias", tags=["Geometrias"])
router.include_router(websocket.router, prefix="/websocket", tags=["WebSocket"])
