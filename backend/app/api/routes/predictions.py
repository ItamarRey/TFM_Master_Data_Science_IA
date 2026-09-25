from fastapi import APIRouter, HTTPException

from backend.app.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter()


@router.post("/", response_model=PredictionResponse)
def create_prediction(request: PredictionRequest) -> PredictionResponse:
    """Punto de conexión para el modelo que se implementará en la siguiente fase."""
    raise HTTPException(
        status_code=501,
        detail=(
            "El endpoint está preparado, pero todavía no se ha conectado el generador "
            "de datos y el modelo de ocupación."
        ),
    )
