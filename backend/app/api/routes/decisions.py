"""Endpoints de registro de acciones simuladas del gestor."""

from fastapi import APIRouter, Query

from backend.app.schemas.decision import DecisionRequest, DecisionResponse
from backend.app.services.decision_service import list_decisions, record_decision

router = APIRouter()


@router.post("/", response_model=DecisionResponse)
def create_decision(request: DecisionRequest) -> DecisionResponse:
    """Registra una decisión simulada sin alterar reservas ni tarifas reales."""
    return DecisionResponse(**record_decision(request))


@router.get("/", response_model=list[DecisionResponse])
def get_decisions(limit: int = Query(default=12, ge=1, le=100)) -> list[DecisionResponse]:
    """Devuelve decisiones locales recientes para la vista de histórico."""
    return [DecisionResponse(**record) for record in list_decisions(limit)]
