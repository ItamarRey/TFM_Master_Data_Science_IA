from fastapi import APIRouter

from backend.app.api.routes import decisions, health, predictions, tariffs, weather

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(tariffs.router, prefix="/tariffs", tags=["tariffs"])
