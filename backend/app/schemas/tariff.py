"""Contratos para las tarifas simuladas programadas en el MVP."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class SimulatedTariffResponse(BaseModel):
    """Tarifa activa de un turno dentro de la simulación local."""

    date: date
    court_id: str = Field(min_length=1)
    start_time: time
    price_eur: float = Field(gt=0)
    scenario: Literal["low", "medium", "high"]
    action: Literal["apply_suggested", "keep_base"]
    action_label: str
    updated_at: datetime
    decision_id: str
