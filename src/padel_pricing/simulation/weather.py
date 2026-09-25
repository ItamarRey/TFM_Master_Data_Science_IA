"""Obtención y simulación controlada de meteorología por hora."""

from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd

from padel_pricing.simulation.config import SimulationConfig


OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather(config: SimulationConfig) -> pd.DataFrame:
    """Devuelve meteorología horaria real o una alternativa sintética explícita.

    La alternativa sintética solo existe para desarrollo sin conexión. El modo por
    defecto usa el archivo histórico público de Open-Meteo configurado en JSON.
    """
    if config.weather.source == "synthetic":
        return generate_synthetic_weather(config)
    return fetch_open_meteo_weather(config)


def fetch_open_meteo_weather(config: SimulationConfig) -> pd.DataFrame:
    params = urlencode(
        {
            "latitude": config.weather.latitude,
            "longitude": config.weather.longitude,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "hourly": "temperature_2m,precipitation,wind_speed_10m",
            "timezone": config.timezone,
        }
    )
    request_url = f"{OPEN_METEO_ARCHIVE_URL}?{params}"
    try:
        # nosec B310: request_url is built from a fixed, public endpoint and numeric configuration.
        with urlopen(request_url, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise RuntimeError(
            "No se pudo obtener la meteorología histórica de Open-Meteo. "
            "Comprueba la conexión o ejecuta con --weather-source synthetic para desarrollo."
        ) from exc

    hourly = payload.get("hourly")
    if not hourly:
        raise RuntimeError("Open-Meteo no devolvió datos horarios para el periodo solicitado.")

    weather = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(hourly["time"]),
            "temperatura_c": hourly["temperature_2m"],
            "precipitacion_mm": hourly["precipitation"],
            "viento_kmh": hourly["wind_speed_10m"],
        }
    )
    return _normalise_weather(weather)


def generate_synthetic_weather(config: SimulationConfig) -> pd.DataFrame:
    """Genera patrones climáticos plausibles de Canarias para pruebas locales."""
    index = pd.date_range(config.start_date, config.end_date + pd.Timedelta(days=1), freq="h")[:-1]
    rng = np.random.default_rng(config.seed + 10_000)
    day_of_year = index.dayofyear.to_numpy()
    hour = index.hour.to_numpy()

    seasonal_temperature = 22.0 + 3.0 * np.sin(2 * np.pi * (day_of_year - 170) / 365)
    daily_temperature = 2.2 * np.sin(2 * np.pi * (hour - 14) / 24)
    temperature = seasonal_temperature + daily_temperature + rng.normal(0, 1.1, len(index))

    rain_probability = 0.04 + 0.12 * (1 - np.sin(2 * np.pi * (day_of_year - 170) / 365)) / 2
    precipitation = np.where(
        rng.random(len(index)) < rain_probability,
        rng.gamma(shape=1.4, scale=0.8, size=len(index)),
        0.0,
    )
    wind = np.clip(16 + rng.normal(0, 5, len(index)) + 2 * np.sin(2 * np.pi * hour / 24), 1, None)

    weather = pd.DataFrame(
        {
            "timestamp": index,
            "temperatura_c": temperature,
            "precipitacion_mm": precipitation,
            "viento_kmh": wind,
        }
    )
    return _normalise_weather(weather)


def _normalise_weather(weather: pd.DataFrame) -> pd.DataFrame:
    result = weather.copy()
    result["date"] = result["timestamp"].dt.date
    result["weather_hour"] = result["timestamp"].dt.hour
    result["temperatura_c"] = result["temperatura_c"].astype(float).round(2)
    result["precipitacion_mm"] = result["precipitacion_mm"].astype(float).clip(lower=0).round(2)
    result["viento_kmh"] = result["viento_kmh"].astype(float).clip(lower=0).round(2)
    return result[
        ["timestamp", "date", "weather_hour", "temperatura_c", "precipitacion_mm", "viento_kmh"]
    ]
