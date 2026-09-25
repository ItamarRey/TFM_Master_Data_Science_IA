from fastapi import APIRouter, HTTPException

from backend.app.schemas.prediction import PredictionRequest, PredictionResponse
from backend.app.services.prediction_service import ModelNotReadyError, predict_turn

router = APIRouter()


@router.post("/", response_model=PredictionResponse)
def create_prediction(request: PredictionRequest) -> PredictionResponse:
    """Predice la ocupación y genera una recomendación de precio revisable."""
    try:
        return PredictionResponse(**predict_turn(request))
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
