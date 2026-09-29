"""Consulta de tarifas programadas dentro de la simulación del MVP."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.schemas.tariff import SimulatedTariffResponse
from backend.app.services.decision_service import list_simulated_tariffs

router = APIRouter()


@router.get("/", response_model=list[SimulatedTariffResponse])
def get_simulated_tariffs(
    selected_date: Annotated[date | None, Query(alias="date")] = None,
) -> list[SimulatedTariffResponse]:
    """Devuelve las tarifas activas generadas por decisiones simuladas."""
    return [SimulatedTariffResponse(**item) for item in list_simulated_tariffs(selected_date)]
