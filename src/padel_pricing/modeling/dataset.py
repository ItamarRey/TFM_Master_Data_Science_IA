"""Preparación del dataset para predicción de ocupación a 48 horas."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


TARGET_COLUMN = "ocupado_final"
TIMESTAMP_COLUMN = "fecha_hora_inicio"
CATEGORICAL_FEATURES = [
    "id_pista",
    "tipo_pista",
    "dia_semana",
    "mes",
    "es_fin_de_semana",
    "es_festivo",
    "franja_horaria",
    "hora_inicio",
    "es_hora_punta",
    "pronostico_temperatura_c_imputado",
    "pronostico_precipitacion_mm_imputado",
    "pronostico_viento_kmh_imputado",
]
NUMERIC_FEATURES = [
    "tarifa_publicada",
    "pronostico_temperatura_c",
    "pronostico_precipitacion_mm",
    "pronostico_viento_kmh",
    "precipitacion_exterior",
    "viento_exterior_exceso",
    "deficit_temperatura_exterior",
]
MODEL_FEATURES = [*CATEGORICAL_FEATURES, *NUMERIC_FEATURES]
SOURCE_FEATURES = [
    "id_pista",
    "tipo_pista",
    "dia_semana",
    "mes",
    "es_fin_de_semana",
    "es_festivo",
    "franja_horaria",
    "pronostico_temperatura_c_imputado",
    "pronostico_precipitacion_mm_imputado",
    "pronostico_viento_kmh_imputado",
    "tarifa_publicada",
    "pronostico_temperatura_c",
    "pronostico_precipitacion_mm",
    "pronostico_viento_kmh",
]


@dataclass(frozen=True)
class TemporalSplit:
    """Partición cronológica que evita evaluar con información del futuro."""

    train: pd.DataFrame
    test: pd.DataFrame
    test_start: pd.Timestamp


def prepare_modeling_data(gold_data: pd.DataFrame) -> pd.DataFrame:
    """Selecciona solo filas y variables disponibles 48 h antes del turno.

    No incorpora resultados operativos finales (cancelación, ingreso, estado de
    reserva ni meteorología observada), porque no se conocerían en el momento
    de realizar la predicción.
    """
    required_columns = {TIMESTAMP_COLUMN, TARGET_COLUMN, "bloqueado", *SOURCE_FEATURES}
    missing_columns = required_columns - set(gold_data.columns)
    if missing_columns:
        raise ValueError(f"Faltan columnas para modelado: {sorted(missing_columns)}")

    selected_columns = [TIMESTAMP_COLUMN, *MODEL_FEATURES, TARGET_COLUMN]
    source_columns = [TIMESTAMP_COLUMN, "bloqueado", TARGET_COLUMN, *SOURCE_FEATURES]
    data = gold_data.loc[~gold_data["bloqueado"], source_columns].copy()
    data[TIMESTAMP_COLUMN] = pd.to_datetime(data[TIMESTAMP_COLUMN], errors="coerce")
    if data[TIMESTAMP_COLUMN].isna().any():
        raise ValueError("fecha_hora_inicio contiene valores no válidos.")
    data = _add_prediction_time_features(data)
    if data[MODEL_FEATURES].isna().any().any():
        raise ValueError("Las variables de entrada no pueden contener nulos tras Silver.")
    if not set(data[TARGET_COLUMN].unique()).issubset({0, 1, False, True}):
        raise ValueError("ocupado_final debe ser una variable binaria.")

    data[TARGET_COLUMN] = data[TARGET_COLUMN].astype(int)
    return data[[TIMESTAMP_COLUMN, *MODEL_FEATURES, TARGET_COLUMN]].sort_values(
        TIMESTAMP_COLUMN
    ).reset_index(drop=True)


def temporal_train_test_split(
    data: pd.DataFrame, test_start: str | pd.Timestamp | None = None
) -> TemporalSplit:
    """Crea un holdout temporal; por defecto, el segundo año se reserva para test."""
    if data.empty:
        raise ValueError("No hay filas disponibles para crear la partición temporal.")

    first_timestamp = pd.Timestamp(data[TIMESTAMP_COLUMN].min())
    split_timestamp = (
        pd.Timestamp(test_start)
        if test_start is not None
        else first_timestamp + pd.DateOffset(years=1)
    )
    train = data.loc[data[TIMESTAMP_COLUMN] < split_timestamp].copy()
    test = data.loc[data[TIMESTAMP_COLUMN] >= split_timestamp].copy()
    if train.empty or test.empty:
        raise ValueError(
            "La fecha de corte temporal debe dejar observaciones tanto para entrenamiento "
            "como para test."
        )
    return TemporalSplit(train=train, test=test, test_start=split_timestamp)


def split_features_target(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Separa las variables explicativas permitidas de la variable objetivo."""
    return data[MODEL_FEATURES].copy(), data[TARGET_COLUMN].copy()


def _add_prediction_time_features(data: pd.DataFrame) -> pd.DataFrame:
    """Crea interacciones conocidas en el momento de la predicción."""
    result = data.copy()
    result["hora_inicio"] = result[TIMESTAMP_COLUMN].dt.hour
    result["es_hora_punta"] = result["hora_inicio"].isin([18, 20])
    exterior = (result["tipo_pista"] == "exterior").astype(int)
    result["precipitacion_exterior"] = result["pronostico_precipitacion_mm"] * exterior
    result["viento_exterior_exceso"] = (
        (result["pronostico_viento_kmh"] - 18).clip(lower=0) * exterior
    )
    result["deficit_temperatura_exterior"] = (
        (18 - result["pronostico_temperatura_c"]).clip(lower=0) * exterior
    )
    return result

