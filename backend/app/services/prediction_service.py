"""Orquestación del modelo de ocupación y la regla de recomendación de tarifa."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from backend.app.schemas.prediction import PredictionRequest
from padel_pricing.modeling.dataset import MODEL_FEATURES
from padel_pricing.pricing import load_pricing_policy, recommend_price
from padel_pricing.simulation.generator import PUBLIC_HOLIDAYS


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "models" / "occupancy_model.joblib"
PRICING_CONFIG_PATH = PROJECT_ROOT / "config" / "pricing_scenarios.json"


class ModelNotReadyError(RuntimeError):
    """Se lanza cuando el artefacto entrenado todavía no existe."""


@lru_cache(maxsize=1)
def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise ModelNotReadyError(
            "No existe el modelo entrenado. Ejecuta scripts/train_occupancy_models.py primero."
        )
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def _load_policy() -> Any:
    return load_pricing_policy(PRICING_CONFIG_PATH)


def predict_turn(request: PredictionRequest) -> dict[str, Any]:
    """Devuelve probabilidad, recomendación y explicación controlada para un turno."""
    model_input = build_model_input(request)
    probability = float(_load_model().predict_proba(model_input)[:, 1][0])
    policy = _load_policy()
    recommendation = recommend_price(
        current_price_eur=request.current_price,
        occupancy_probability=probability,
        scenario_name=request.scenario,
        policy=policy,
    )
    return {
        "occupancy_probability": round(probability, 4),
        "current_price": recommendation.current_price_eur,
        "suggested_price": recommendation.suggested_price_eur,
        "variation_pct": recommendation.variation_pct,
        "scenario": recommendation.scenario,
        "scenario_label": recommendation.scenario_label,
        "simulated_occupancy_probability": recommendation.simulated_occupancy_probability,
        "expected_revenue_current": recommendation.expected_revenue_current_eur,
        "expected_revenue_suggested": recommendation.expected_revenue_suggested_eur,
        "candidates": [candidate.__dict__ for candidate in recommendation.candidates],
        "explanation": _build_explanation(request, probability, recommendation.explanation),
        "warning": "Datos sintéticos · La recomendación es un escenario y requiere revisión.",
    }


def build_model_input(request: PredictionRequest) -> pd.DataFrame:
    """Transforma la entrada de API en las mismas variables usadas al entrenar."""
    court_type = _court_type(request.court_id)
    timestamp = datetime.combine(request.date, request.start_time)
    hour = timestamp.hour
    exterior = int(court_type == "exterior")
    row = {
        "id_pista": request.court_id,
        "tipo_pista": court_type,
        "dia_semana": timestamp.strftime("%A"),
        "mes": timestamp.month,
        "es_fin_de_semana": timestamp.weekday() >= 5,
        "es_festivo": (timestamp.month, timestamp.day) in PUBLIC_HOLIDAYS,
        "franja_horaria": _time_band(hour),
        "hora_inicio": hour,
        "es_hora_punta": hour in {18, 20},
        "pronostico_temperatura_c_imputado": False,
        "pronostico_precipitacion_mm_imputado": False,
        "pronostico_viento_kmh_imputado": False,
        "tarifa_publicada": request.current_price,
        "pronostico_temperatura_c": request.forecast_temperature_c,
        "pronostico_precipitacion_mm": request.forecast_precipitation_mm,
        "pronostico_viento_kmh": request.forecast_wind_kmh,
        "precipitacion_exterior": request.forecast_precipitation_mm * exterior,
        "viento_exterior_exceso": max(0.0, request.forecast_wind_kmh - 18) * exterior,
        "deficit_temperatura_exterior": max(0.0, 18 - request.forecast_temperature_c)
        * exterior,
    }
    return pd.DataFrame([row], columns=MODEL_FEATURES)


def _court_type(court_id: str) -> str:
    if court_id.startswith("exterior_"):
        return "exterior"
    if court_id.startswith("interior_"):
        return "interior"
    raise ValueError("court_id debe comenzar por 'exterior_' o 'interior_'.")


def _time_band(hour: int) -> str:
    if hour < 12:
        return "mañana"
    if hour < 17:
        return "mediodía"
    if hour < 20:
        return "tarde"
    return "noche"


def _build_explanation(
    request: PredictionRequest, probability: float, pricing_explanation: str
) -> list[str]:
    items = [pricing_explanation]
    if probability < 0.35:
        items.append("La probabilidad estimada indica una demanda baja para este turno.")
    elif probability > 0.65:
        items.append("La probabilidad estimada indica una demanda alta para este turno.")
    else:
        items.append("La demanda estimada se encuentra en un rango intermedio.")
    if request.start_time.hour in {18, 20}:
        items.append("La hora seleccionada corresponde a una franja de alta demanda simulada.")
    if request.court_id.startswith("exterior_") and request.forecast_precipitation_mm > 0:
        items.append("La lluvia prevista reduce la demanda estimada en pistas exteriores.")
    if request.date.weekday() >= 5:
        items.append("El fin de semana se incorpora como factor de mayor demanda simulada.")
    return items
