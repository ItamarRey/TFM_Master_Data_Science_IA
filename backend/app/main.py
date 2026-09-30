from fastapi import FastAPI

from backend.app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PádelPulse API",
        version="0.1.0",
        description="API del MVP de predicción de ocupación y recomendación de tarifas.",
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
