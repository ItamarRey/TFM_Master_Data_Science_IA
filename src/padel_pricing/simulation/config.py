"""Configuración explícita y reproducible de la simulación."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Court:
    """Características estables de una pista simulada."""

    court_id: str
    court_type: str


@dataclass(frozen=True)
class WeatherConfig:
    source: str
    location_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class DataQualityConfig:
    """Tasas de incidencias sintéticas usadas para probar la capa Silver."""

    inject_controlled_issues: bool
    duplicate_rate: float
    date_format_issue_rate: float
    price_format_issue_rate: float
    category_format_issue_rate: float
    forecast_missing_rate: float


@dataclass(frozen=True)
class SimulationConfig:
    start_date: date
    end_date: date
    seed: int
    timezone: str
    slot_duration_minutes: int
    slot_start_times: tuple[str, ...]
    courts: tuple[Court, ...]
    weather: WeatherConfig
    base_price_eur: float
    price_sensitivity: str
    cancellation_rate: float
    no_show_rate: float
    maintenance_block_rate: float
    tournament_block_rate: float
    data_quality: DataQualityConfig

    @property
    def expected_slots(self) -> int:
        days = (self.end_date - self.start_date).days + 1
        return days * len(self.slot_start_times) * len(self.courts)


def load_simulation_config(path: Path) -> SimulationConfig:
    """Carga y valida la configuración que documenta los supuestos."""
    payload = json.loads(path.read_text(encoding="utf-8"))["simulation"]
    weather = payload["weather"]
    occupancy = payload["occupancy"]
    operational = payload["operational"]
    quality = payload["data_quality"]

    config = SimulationConfig(
        start_date=date.fromisoformat(payload["start_date"]),
        end_date=date.fromisoformat(payload["end_date"]),
        seed=int(payload["seed"]),
        timezone=payload["timezone"],
        slot_duration_minutes=int(payload["slot_duration_minutes"]),
        slot_start_times=tuple(payload["slot_start_times"]),
        courts=tuple(
            Court(court_id=item["id"], court_type=item["type"])
            for item in payload["courts"]
        ),
        weather=WeatherConfig(
            source=weather["source"],
            location_name=weather["location_name"],
            latitude=float(weather["latitude"]),
            longitude=float(weather["longitude"]),
        ),
        base_price_eur=float(occupancy["base_price_eur"]),
        price_sensitivity=occupancy["price_sensitivity"],
        cancellation_rate=float(occupancy["cancellation_rate"]),
        no_show_rate=float(occupancy["no_show_rate"]),
        maintenance_block_rate=float(operational["maintenance_block_rate"]),
        tournament_block_rate=float(operational["tournament_block_rate"]),
        data_quality=DataQualityConfig(
            inject_controlled_issues=bool(quality["inject_controlled_issues"]),
            duplicate_rate=float(quality["duplicate_rate"]),
            date_format_issue_rate=float(quality["date_format_issue_rate"]),
            price_format_issue_rate=float(quality["price_format_issue_rate"]),
            category_format_issue_rate=float(quality["category_format_issue_rate"]),
            forecast_missing_rate=float(quality["forecast_missing_rate"]),
        ),
    )
    if config.end_date < config.start_date:
        raise ValueError("end_date debe ser igual o posterior a start_date")
    if config.weather.source not in {"open-meteo", "synthetic"}:
        raise ValueError("weather.source debe ser 'open-meteo' o 'synthetic'")
    if config.price_sensitivity not in {"low", "medium", "high"}:
        raise ValueError("price_sensitivity debe ser low, medium o high")
    rates = (
        config.data_quality.duplicate_rate,
        config.data_quality.date_format_issue_rate,
        config.data_quality.price_format_issue_rate,
        config.data_quality.category_format_issue_rate,
        config.data_quality.forecast_missing_rate,
    )
    if any(not 0 <= rate < 1 for rate in rates):
        raise ValueError("Las tasas de calidad deben estar entre 0 (incluido) y 1 (excluido)")
    return config
