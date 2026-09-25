"""Pipeline de calidad para el extracto operativo simulado.

La simulación crea primero una verdad operativa interna y limpia. Después se
inyectan incidencias pequeñas, reproducibles y documentadas en Raw. Silver
normaliza los datos sin usar esa verdad interna: aplica las mismas reglas que
usaríamos frente a un CSV exportado por un sistema de reservas.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from padel_pricing.simulation.config import SimulationConfig


FORECAST_COLUMNS = [
    "pronostico_temperatura_c",
    "pronostico_precipitacion_mm",
    "pronostico_viento_kmh",
]
NUMERIC_COLUMNS = [
    "duracion_minutos",
    "mes",
    "tarifa_publicada",
    "temperatura_c",
    "precipitacion_mm",
    "viento_kmh",
    *FORECAST_COLUMNS,
    "anticipacion_reserva_dias",
    "ingreso_final",
]
BOOLEAN_COLUMNS = ["es_fin_de_semana", "es_festivo", "bloqueado", "cancelado", "no_show", "ocupado_final"]
GOLD_COLUMNS = [
    "id_slot",
    "fecha_hora_inicio",
    "duracion_minutos",
    "id_pista",
    "tipo_pista",
    "dia_semana",
    "mes",
    "es_fin_de_semana",
    "es_festivo",
    "nombre_festivo",
    "franja_horaria",
    "tarifa_publicada",
    "temperatura_c",
    "precipitacion_mm",
    "viento_kmh",
    *FORECAST_COLUMNS,
    "pronostico_temperatura_c_imputado",
    "pronostico_precipitacion_mm_imputado",
    "pronostico_viento_kmh_imputado",
    "bloqueado",
    "motivo_bloqueo",
    "estado_reserva",
    "cancelado",
    "no_show",
    "ocupado_final",
    "anticipacion_reserva_dias",
    "ingreso_final",
]


def inject_controlled_issues(
    clean_data: pd.DataFrame, config: SimulationConfig
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Convierte una tabla operativa limpia en un extracto Raw realista.

    Las incidencias solo verifican la robustez de la limpieza. No representan
    observaciones de un club ni se incorporan como señal al modelo.
    """
    raw = clean_data.copy()
    raw["source_record_id"] = [f"src_{index:06d}" for index in range(1, len(raw) + 1)]
    raw["fecha_hora_inicio"] = pd.to_datetime(raw["fecha_hora_inicio"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    quality = config.data_quality
    if not quality.inject_controlled_issues:
        return raw, {"enabled": False, "rows_added_as_duplicates": 0}

    rng = np.random.default_rng(config.seed + 20_000)
    injected = {"enabled": True}

    duplicate_count = _rate_count(len(raw), quality.duplicate_rate)
    duplicate_rows = raw.iloc[_sample_positions(rng, len(raw), duplicate_count)].copy()
    duplicate_rows["source_record_id"] = [
        f"src_dup_{index:06d}" for index in range(1, len(duplicate_rows) + 1)
    ]
    raw = pd.concat([raw, duplicate_rows], ignore_index=True)
    injected["rows_added_as_duplicates"] = duplicate_count

    date_count = _rate_count(len(clean_data), quality.date_format_issue_rate)
    date_positions = _sample_positions(rng, len(clean_data), date_count)
    raw.loc[date_positions, "fecha_hora_inicio"] = pd.to_datetime(
        raw.loc[date_positions, "fecha_hora_inicio"]
    ).dt.strftime("%d/%m/%Y %H:%M")
    injected["date_format_issues"] = date_count

    price_count = _rate_count(len(clean_data), quality.price_format_issue_rate)
    price_positions = _sample_positions(rng, len(clean_data), price_count)
    raw["tarifa_publicada"] = raw["tarifa_publicada"].astype(object)
    raw.loc[price_positions, "tarifa_publicada"] = raw.loc[
        price_positions, "tarifa_publicada"
    ].map(lambda value: f"{float(value):.2f} €".replace(".", ","))
    injected["price_format_issues"] = price_count

    category_count = _rate_count(len(clean_data), quality.category_format_issue_rate)
    category_positions = _sample_positions(rng, len(clean_data), category_count)
    for position in category_positions:
        raw.loc[position, "id_pista"] = f" {str(raw.loc[position, 'id_pista']).upper()} "
        raw.loc[position, "tipo_pista"] = f" {str(raw.loc[position, 'tipo_pista']).title()} "
        raw.loc[position, "estado_reserva"] = f" {str(raw.loc[position, 'estado_reserva']).upper()} "
    injected["category_format_issues"] = category_count

    missing_count = _rate_count(len(clean_data), quality.forecast_missing_rate)
    missing_positions = _sample_positions(rng, len(clean_data), missing_count)
    missing_by_column = {column: 0 for column in FORECAST_COLUMNS}
    for index, position in enumerate(missing_positions):
        column = FORECAST_COLUMNS[index % len(FORECAST_COLUMNS)]
        raw.loc[position, column] = None
        missing_by_column[column] += 1
    injected["forecast_missing_values"] = missing_by_column
    return raw, injected


def clean_operational_data(raw_data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Limpia un extracto de reservas y emite métricas de calidad auditables."""
    required_columns = set(GOLD_COLUMNS) - {
        "pronostico_temperatura_c_imputado",
        "pronostico_precipitacion_mm_imputado",
        "pronostico_viento_kmh_imputado",
    }
    missing_columns = required_columns - set(raw_data.columns)
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing_columns)}")

    data = raw_data.copy()
    report: dict[str, Any] = {"rows_read_raw": len(data)}

    raw_id_slot = data["id_slot"].astype("string").str.strip()
    duplicate_mask = raw_id_slot.duplicated(keep="first")
    report["duplicate_rows_removed"] = int(duplicate_mask.sum())
    data = data.loc[~duplicate_mask].copy()

    raw_datetime = data["fecha_hora_inicio"].astype("string").str.strip()
    report["datetime_formats_normalised"] = int((~raw_datetime.str.match(r"^\d{4}-\d{2}-\d{2}T")).sum())
    data["fecha_hora_inicio"] = _parse_datetime(raw_datetime)

    raw_price = data["tarifa_publicada"].astype("string").str.strip()
    report["price_formats_normalised"] = int(raw_price.str.contains(r"[,€]", regex=True).sum())
    data["tarifa_publicada"] = _parse_price(raw_price)

    category_corrections = 0
    for column in ("id_pista", "tipo_pista", "estado_reserva"):
        raw_value = data[column].astype("string")
        normalised = raw_value.str.strip().str.lower()
        category_corrections += int((raw_value != normalised).sum())
        data[column] = normalised
    report["category_values_normalised"] = category_corrections

    for column in ("nombre_festivo", "motivo_bloqueo"):
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    for column in BOOLEAN_COLUMNS:
        data[column] = _parse_boolean(data[column], column)

    essential = ["id_slot", "fecha_hora_inicio", "id_pista", "tipo_pista", "tarifa_publicada"]
    missing_essential = data[essential].isna().any(axis=1)
    if missing_essential.any():
        raise ValueError(
            "Hay registros sin información esencial; deben pasar a una cuarentena explícita. "
            f"Filas afectadas: {int(missing_essential.sum())}."
        )

    imputed: dict[str, int] = {}
    for column in FORECAST_COLUMNS:
        missing = data[column].isna()
        imputed[column] = int(missing.sum())
        if missing.any():
            median = data[column].median(skipna=True)
            if pd.isna(median):
                raise ValueError(f"No se puede imputar {column}: no hay valores válidos.")
            data.loc[missing, column] = median
        data[f"{column}_imputado"] = missing.astype(bool)
    report["forecast_values_imputed"] = imputed

    _validate_silver_contract(data)
    data = data[GOLD_COLUMNS].copy()
    data["duracion_minutos"] = data["duracion_minutos"].astype(int)
    data["mes"] = data["mes"].astype(int)
    data["anticipacion_reserva_dias"] = data["anticipacion_reserva_dias"].astype("Int64")
    report["rows_written_silver"] = len(data)
    return data, report


def build_gold_dataset(silver_data: pd.DataFrame, config: SimulationConfig) -> pd.DataFrame:
    """Publica Gold solo si Silver cumple el contrato del caso de uso."""
    gold = silver_data[GOLD_COLUMNS].copy()
    _validate_silver_contract(gold)
    if len(gold) != config.expected_slots:
        raise ValueError("Gold no conserva el número esperado de turnos de la simulación.")
    if not gold["id_slot"].is_unique:
        raise ValueError("Gold no puede contener id_slot duplicados.")
    return gold


def _rate_count(size: int, rate: float) -> int:
    return int(round(size * rate))


def _sample_positions(rng: np.random.Generator, size: int, count: int) -> np.ndarray:
    if count == 0:
        return np.array([], dtype=int)
    return rng.choice(size, size=count, replace=False)


def _parse_datetime(values: pd.Series) -> pd.Series:
    iso_mask = values.str.match(r"^\d{4}-\d{2}-\d{2}T")
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    result.loc[iso_mask] = pd.to_datetime(values.loc[iso_mask], errors="coerce")
    result.loc[~iso_mask] = pd.to_datetime(values.loc[~iso_mask], errors="coerce", dayfirst=True)
    return result


def _parse_price(values: pd.Series) -> pd.Series:
    cleaned = values.str.replace("€", "", regex=False).str.replace(" ", "", regex=False)
    return pd.to_numeric(cleaned.str.replace(",", ".", regex=False), errors="coerce")


def _parse_boolean(values: pd.Series, column: str) -> pd.Series:
    normalised = values.astype("string").str.strip().str.lower()
    parsed = normalised.map({"true": True, "false": False, "1": True, "0": False})
    if parsed.isna().any():
        raise ValueError(f"Valores booleanos no válidos en {column}.")
    return parsed.astype(bool)


def _validate_silver_contract(data: pd.DataFrame) -> None:
    if not data["id_slot"].is_unique:
        raise ValueError("id_slot debe ser único tras la limpieza.")
    if not set(data["tipo_pista"].dropna()).issubset({"interior", "exterior"}):
        raise ValueError("tipo_pista contiene categorías no reconocidas.")
    allowed_status = {"bloqueado", "libre", "cancelado", "no_show", "confirmado"}
    if not set(data["estado_reserva"].dropna()).issubset(allowed_status):
        raise ValueError("estado_reserva contiene categorías no reconocidas.")
    if data["tarifa_publicada"].isna().any() or (data["tarifa_publicada"] <= 0).any():
        raise ValueError("tarifa_publicada debe ser positiva y no nula.")
    required_numeric = [
        "duracion_minutos",
        "mes",
        "temperatura_c",
        "precipitacion_mm",
        "viento_kmh",
        "ingreso_final",
    ]
    if data[required_numeric].isna().any().any():
        raise ValueError("Faltan valores en campos numéricos operativos obligatorios.")
    if data.loc[data["bloqueado"], "ocupado_final"].any():
        raise ValueError("Un turno bloqueado no puede estar ocupado.")
    if data.loc[data["cancelado"], "ocupado_final"].any():
        raise ValueError("Una reserva cancelada no puede contar como ocupada.")
    if not (data.loc[data["bloqueado"], "estado_reserva"] == "bloqueado").all():
        raise ValueError("Un turno bloqueado debe tener estado_reserva='bloqueado'.")
    expected_income = (data["tarifa_publicada"] * data["ocupado_final"]).round(2)
    if not np.allclose(data["ingreso_final"], expected_income, atol=0.01, equal_nan=False):
        raise ValueError("ingreso_final no es coherente con tarifa_publicada y ocupado_final.")
