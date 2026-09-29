from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.app.schemas.weather import WeatherForecastResponse


class PredictionRequest(BaseModel):
    date: date
    court_id: Literal[
        "exterior_1", "exterior_2", "exterior_3", "exterior_4", "interior_1", "interior_2"
    ] = Field(examples=["exterior_2"])
    start_time: time = Field(examples=["18:30"])
    current_price: float = Field(gt=0, examples=[12.0])
    scenario: Literal["low", "medium", "high"] = "medium"
    weather_mode: Literal["automatic", "simulation"] = "automatic"
    forecast_temperature_c: float | None = Field(default=None, examples=[22.0])
    forecast_precipitation_mm: float | None = Field(default=None, ge=0, examples=[0.0])
    forecast_wind_kmh: float | None = Field(default=None, ge=0, examples=[15.0])

    @model_validator(mode="after")
    def validate_simulated_weather(self) -> "PredictionRequest":
        if self.weather_mode == "simulation" and any(
            value is None
            for value in (
                self.forecast_temperature_c,
                self.forecast_precipitation_mm,
                self.forecast_wind_kmh,
            )
        ):
            raise ValueError(
                "La simulación manual requiere temperatura, lluvia y viento previstos."
            )
        return self


class PriceCandidateResponse(BaseModel):
    price_eur: float
    variation_pct: float
    simulated_occupancy_probability: float
    simulated_expected_revenue_eur: float
    is_allowed: bool = True


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
    weather: WeatherForecastResponse
    explanation: list[str]
    warning: str
