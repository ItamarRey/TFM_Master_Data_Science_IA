"""Contratos de la API para registrar decisiones simuladas del gestor."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    action: Literal["apply_suggested", "keep_base"]
    date: date
    court_id: str = Field(min_length=1)
    start_time: time
    scenario: Literal["low", "medium", "high"]
    occupancy_probability: float = Field(ge=0, le=1)
    current_price: float = Field(gt=0)
    suggested_price: float = Field(gt=0)


class DecisionResponse(DecisionRequest):
    id: str
    created_at: datetime
    action_label: str
    applied_price_eur: float | None = None
