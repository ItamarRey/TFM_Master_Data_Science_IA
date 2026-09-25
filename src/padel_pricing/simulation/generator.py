"""Generador reproducible de turnos, reservas y resultados operativos."""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd

from padel_pricing.simulation.config import SimulationConfig


ELASTICITY_BY_SCENARIO = {"low": 0.10, "medium": 0.28, "high": 0.46}
PUBLIC_HOLIDAYS = {
    (1, 1): "Año Nuevo",
    (1, 6): "Epifanía",
    (5, 1): "Día del Trabajo",
    (8, 15): "Asunción",
    (10, 12): "Fiesta Nacional",
    (11, 1): "Todos los Santos",
    (12, 6): "Constitución",
    (12, 8): "Inmaculada",
    (12, 25): "Navidad",
}


def generate_operational_data(config: SimulationConfig, weather: pd.DataFrame) -> pd.DataFrame:
    """Genera una fila por pista y turno, sin usar información futura en las entradas.

    `ocupado_final` es 1 cuando una reserva confirmada asigna el turno a un cliente.
    Un no-show sigue contando como ocupado: la pista no se pudo vender a otra persona.
    Las cancelaciones y los bloqueos no cuentan como ocupación final.
    """
    rng = np.random.default_rng(config.seed)
    rows: list[dict[str, object]] = []
    dates = pd.date_range(config.start_date, config.end_date, freq="D")
    weather_lookup = weather.set_index(["date", "weather_hour"])

    court_effect = {court.court_id: rng.normal(0, 0.12) for court in config.courts}
    for day_timestamp in dates:
        day = day_timestamp.date()
        holiday_name = PUBLIC_HOLIDAYS.get((day.month, day.day))
        for slot_time in config.slot_start_times:
            hour, minute = (int(value) for value in slot_time.split(":"))
            start = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
            weather_row = weather_lookup.loc[(day, hour)]
            for court in config.courts:
                price = _published_price(config.base_price_eur, day, hour, court.court_type)
                blocked, block_reason = _blocked_status(config, day, rng)
                probability = _occupancy_probability(
                    day=day,
                    hour=hour,
                    court_type=court.court_type,
                    price=price,
                    base_price=config.base_price_eur,
                    temperature=float(weather_row["temperatura_c"]),
                    precipitation=float(weather_row["precipitacion_mm"]),
                    wind=float(weather_row["viento_kmh"]),
                    court_effect=float(court_effect[court.court_id]),
                    price_sensitivity=config.price_sensitivity,
                    rng=rng,
                )
                reservation = (not blocked) and rng.random() < probability
                cancelled = reservation and rng.random() < config.cancellation_rate
                no_show = reservation and not cancelled and rng.random() < config.no_show_rate
                occupied_final = int(reservation and not cancelled)
                status = _reservation_status(blocked, reservation, cancelled, no_show)
                forecast = _forecast_from_weather(weather_row, rng)

                rows.append(
                    {
                        "id_slot": f"{start:%Y%m%d_%H%M}_{court.court_id}",
                        "fecha_hora_inicio": start,
                        "duracion_minutos": config.slot_duration_minutes,
                        "id_pista": court.court_id,
                        "tipo_pista": court.court_type,
                        "dia_semana": start.strftime("%A"),
                        "mes": start.month,
                        "es_fin_de_semana": start.weekday() >= 5,
                        "es_festivo": holiday_name is not None,
                        "nombre_festivo": holiday_name,
                        "franja_horaria": _time_band(hour),
                        "tarifa_publicada": price,
                        "temperatura_c": float(weather_row["temperatura_c"]),
                        "precipitacion_mm": float(weather_row["precipitacion_mm"]),
                        "viento_kmh": float(weather_row["viento_kmh"]),
                        "pronostico_temperatura_c": forecast["temperature"],
                        "pronostico_precipitacion_mm": forecast["precipitation"],
                        "pronostico_viento_kmh": forecast["wind"],
                        "bloqueado": blocked,
                        "motivo_bloqueo": block_reason,
                        "estado_reserva": status,
                        "cancelado": cancelled,
                        "no_show": no_show,
                        "ocupado_final": occupied_final,
                        "anticipacion_reserva_dias": _booking_lead_days(reservation, rng),
                        "ingreso_final": round(price * occupied_final, 2),
                    }
                )

    result = pd.DataFrame(rows)
    _validate_operational_data(result, config)
    return result


def _published_price(base_price: float, day: date, hour: int, court_type: str) -> float:
    peak_supplement = 2.0 if hour in {18, 20} else 0.0
    weekend_supplement = 0.5 if day.weekday() >= 5 else 0.0
    indoor_supplement = 0.5 if court_type == "interior" else 0.0
    return round(base_price + peak_supplement + weekend_supplement + indoor_supplement, 2)


def _blocked_status(
    config: SimulationConfig, day: date, rng: np.random.Generator
) -> tuple[bool, str | None]:
    if day.weekday() == 5 and rng.random() < config.tournament_block_rate:
        return True, "torneo"
    if rng.random() < config.maintenance_block_rate:
        return True, "mantenimiento"
    return False, None


def _occupancy_probability(
    *,
    day: date,
    hour: int,
    court_type: str,
    price: float,
    base_price: float,
    temperature: float,
    precipitation: float,
    wind: float,
    court_effect: float,
    price_sensitivity: str,
    rng: np.random.Generator,
) -> float:
    score = -0.65
    if hour in {18, 20}:
        score += 1.25
    elif hour in {17, 21}:
        score += 0.55
    elif hour in {8, 9, 11, 12, 14, 15}:
        score -= 0.30
    if day.weekday() >= 5:
        score += 0.55
    if (day.month, day.day) in PUBLIC_HOLIDAYS:
        score += 0.35
    if day.month in {7, 8}:
        score += 0.20
    if court_type == "interior":
        score += 0.12
    else:
        score -= min(1.40, precipitation * 0.80)
        score -= max(0.0, wind - 18) * 0.025
        score -= max(0.0, 18 - temperature) * 0.05
    score -= ELASTICITY_BY_SCENARIO[price_sensitivity] * (price - base_price)
    score += court_effect + rng.normal(0, 0.30)
    return float(1 / (1 + np.exp(-score)))


def _forecast_from_weather(weather_row: pd.Series, rng: np.random.Generator) -> dict[str, float]:
    return {
        "temperature": round(float(weather_row["temperatura_c"]) + rng.normal(0, 1.2), 2),
        "precipitation": round(
            max(0.0, float(weather_row["precipitacion_mm"]) + rng.normal(0, 0.35)), 2
        ),
        "wind": round(max(0.0, float(weather_row["viento_kmh"]) + rng.normal(0, 3.0)), 2),
    }


def _reservation_status(blocked: bool, reservation: bool, cancelled: bool, no_show: bool) -> str:
    if blocked:
        return "bloqueado"
    if not reservation:
        return "libre"
    if cancelled:
        return "cancelado"
    if no_show:
        return "no_show"
    return "confirmado"


def _booking_lead_days(reservation: bool, rng: np.random.Generator) -> int | None:
    if not reservation:
        return None
    return int(rng.integers(0, 22))


def _time_band(hour: int) -> str:
    if hour < 12:
        return "mañana"
    if hour < 17:
        return "mediodía"
    if hour < 20:
        return "tarde"
    return "noche"


def _validate_operational_data(data: pd.DataFrame, config: SimulationConfig) -> None:
    if len(data) != config.expected_slots:
        raise ValueError("El número de turnos generados no coincide con la configuración.")
    if not data["id_slot"].is_unique:
        raise ValueError("id_slot debe ser único.")
    if data.loc[data["bloqueado"], "ocupado_final"].any():
        raise ValueError("Un turno bloqueado no puede estar ocupado.")
