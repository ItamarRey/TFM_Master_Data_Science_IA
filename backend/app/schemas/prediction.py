from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    date: date
    court_id: str = Field(min_length=1, examples=["exterior_2"])
    start_time: time = Field(examples=["19:30"])
    base_price: float = Field(gt=0, examples=[12.0])
    scenario: Literal["low", "medium", "high"] = "medium"


class PredictionResponse(BaseModel):
    occupancy_probability: float = Field(ge=0, le=1)
    suggested_price: float = Field(gt=0)
    scenario: str
    explanation: list[str]
