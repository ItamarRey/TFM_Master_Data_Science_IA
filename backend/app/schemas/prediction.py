from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    date: date
    court_id: Literal[
        "exterior_1", "exterior_2", "exterior_3", "exterior_4", "interior_1", "interior_2"
    ] = Field(examples=["exterior_2"])
    start_time: time = Field(examples=["18:30"])
    current_price: float = Field(gt=0, examples=[12.0])
    scenario: Literal["low", "medium", "high"] = "medium"
    forecast_temperature_c: float = Field(examples=[22.0])
    forecast_precipitation_mm: float = Field(ge=0, examples=[0.0])
    forecast_wind_kmh: float = Field(ge=0, examples=[15.0])


class PriceCandidateResponse(BaseModel):
    price_eur: float
    variation_pct: float
    simulated_occupancy_probability: float
    simulated_expected_revenue_eur: float


class PredictionResponse(BaseModel):
    occupancy_probability: float = Field(ge=0, le=1)
    current_price: float = Field(gt=0)
    suggested_price: float = Field(gt=0)
    variation_pct: float
    scenario: Literal["low", "medium", "high"]
    scenario_label: str
    simulated_occupancy_probability: float = Field(ge=0, le=1)
    expected_revenue_current: float = Field(ge=0)
    expected_revenue_suggested: float = Field(ge=0)
    candidates: list[PriceCandidateResponse]
    explanation: list[str]
    warning: str
