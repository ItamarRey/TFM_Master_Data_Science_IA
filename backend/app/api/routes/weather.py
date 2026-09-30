"""Ruta informativa de previsión meteorológica para el frontend."""

from datetime import date, time

from fastapi import APIRouter, HTTPException

from backend.app.schemas.weather import WeatherForecastResponse
from backend.app.services.weather_service import (
    WeatherForecastUnavailableError,
    WeatherProviderError,
    fetch_turn_weather,
)

router = APIRouter()


@router.get("/forecast", response_model=WeatherForecastResponse)
def get_forecast(selected_date: date, start_time: time) -> WeatherForecastResponse:
    """Devuelve la previsión pública del club para la hora de inicio del turno."""
    try:
        return fetch_turn_weather(selected_date, start_time).as_response()
    except WeatherForecastUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
