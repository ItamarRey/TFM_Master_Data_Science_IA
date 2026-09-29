"""Contratos de la previsión meteorológica usada por el MVP."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field


class WeatherForecastResponse(BaseModel):
    """Previsión horaria normalizada para un turno de pádel."""

    date: date
    start_time: time
    weather_time: time
    temperature_c: float = Field(examples=[22.0])
    precipitation_mm: float = Field(ge=0, examples=[0.0])
    wind_kmh: float = Field(ge=0, examples=[15.0])
    condition: str = Field(examples=["Despejado"])
    source: Literal["open-meteo", "manual_simulation"]
    source_label: str
    is_simulation: bool
