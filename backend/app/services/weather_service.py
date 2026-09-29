"""Consulta y normalización de la previsión pública para el club configurado."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Any

import httpx

from backend.app.schemas.weather import WeatherForecastResponse

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SIMULATION_CONFIG_PATH = PROJECT_ROOT / "config" / "simulation_config.json"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherProviderError(RuntimeError):
    """La previsión pública no se ha podido recuperar."""


class WeatherForecastUnavailableError(ValueError):
    """No existe una previsión horaria para el turno solicitado."""


@dataclass(frozen=True)
class TurnWeather:
    """Valores meteorológicos listos para consumir por el modelo."""

    date: date
    start_time: time
    weather_time: time
    temperature_c: float
    precipitation_mm: float
    wind_kmh: float
    condition: str
    source: str
    source_label: str
    is_simulation: bool

    def as_response(self) -> WeatherForecastResponse:
        return WeatherForecastResponse(
            date=self.date,
            start_time=self.start_time,
            weather_time=self.weather_time,
            temperature_c=self.temperature_c,
            precipitation_mm=self.precipitation_mm,
            wind_kmh=self.wind_kmh,
            condition=self.condition,
            source=self.source,
            source_label=self.source_label,
            is_simulation=self.is_simulation,
        )


def fetch_turn_weather(selected_date: date, start_time: time) -> TurnWeather:
    """Recupera la hora de previsión asociada al inicio del turno.

    El conjunto de entrenamiento trabaja con franjas horarias: para un turno de
    18:30 se usa la previsión de las 18:00, igual que en la generación de datos.
    """
    weather_config = _load_weather_config()
    params = {
        "latitude": weather_config["latitude"],
        "longitude": weather_config["longitude"],
        "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
        "timezone": weather_config["timezone"],
        "start_date": selected_date.isoformat(),
        "end_date": selected_date.isoformat(),
    }
    try:
        response = httpx.get(OPEN_METEO_FORECAST_URL, params=params, timeout=8.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise WeatherProviderError(
            "No se pudo consultar la previsión meteorológica pública. Inténtalo de nuevo."
        ) from exc

    hourly = _hourly_payload(response.json())
    weather_hour = time(hour=start_time.hour)
    expected_timestamp = f"{selected_date.isoformat()}T{weather_hour.strftime('%H:%M')}"
    try:
        index = hourly["time"].index(expected_timestamp)
    except ValueError as exc:
        raise WeatherForecastUnavailableError(
            "No hay previsión pública disponible para ese turno. "
            "Puedes seleccionar otra fecha o activar la simulación manual."
        ) from exc

    weather_code = int(hourly["weather_code"][index])
    return TurnWeather(
        date=selected_date,
        start_time=start_time,
        weather_time=weather_hour,
        temperature_c=round(float(hourly["temperature_2m"][index]), 1),
        precipitation_mm=round(max(0.0, float(hourly["precipitation"][index])), 1),
        wind_kmh=round(max(0.0, float(hourly["wind_speed_10m"][index])), 1),
        condition=_weather_label(weather_code),
        source="open-meteo",
        source_label="Open-Meteo · previsión automática",
        is_simulation=False,
    )


def simulated_turn_weather(
    selected_date: date,
    start_time: time,
    temperature_c: float,
    precipitation_mm: float,
    wind_kmh: float,
) -> TurnWeather:
    """Crea un escenario manual, separado explícitamente de una previsión real."""
    return TurnWeather(
        date=selected_date,
        start_time=start_time,
        weather_time=time(hour=start_time.hour),
        temperature_c=round(temperature_c, 1),
        precipitation_mm=round(max(0.0, precipitation_mm), 1),
        wind_kmh=round(max(0.0, wind_kmh), 1),
        condition="Condiciones simuladas",
        source="manual_simulation",
        source_label="Simulación manual",
        is_simulation=True,
    )


def _load_weather_config() -> dict[str, Any]:
    payload = json.loads(SIMULATION_CONFIG_PATH.read_text(encoding="utf-8"))
    weather = payload["simulation"]["weather"]
    return {
        "latitude": float(weather["latitude"]),
        "longitude": float(weather["longitude"]),
        "timezone": payload["simulation"]["timezone"],
    }


def _hourly_payload(payload: dict[str, Any]) -> dict[str, list[Any]]:
    hourly = payload.get("hourly")
    required = {"time", "temperature_2m", "precipitation", "wind_speed_10m", "weather_code"}
    if not isinstance(hourly, dict) or not required.issubset(hourly):
        raise WeatherProviderError(
            "La respuesta meteorológica recibida no tiene el formato esperado."
        )
    return hourly


def _weather_label(weather_code: int) -> str:
    if weather_code == 0:
        return "Despejado"
    if weather_code in {1, 2}:
        return "Poco nuboso"
    if weather_code == 3:
        return "Cubierto"
    if weather_code in {45, 48}:
        return "Niebla"
    if weather_code in {51, 53, 55, 56, 57}:
        return "Llovizna"
    if weather_code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Lluvia"
    if weather_code in {71, 73, 75, 77, 85, 86}:
        return "Nieve"
    if weather_code in {95, 96, 99}:
        return "Tormenta"
    return "Condiciones variables"
