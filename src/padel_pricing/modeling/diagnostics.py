"""Diagnósticos de calibración y errores por segmento para modelos probabilísticos."""

from __future__ import annotations

import numpy as np
import pandas as pd

from padel_pricing.modeling.dataset import TARGET_COLUMN


def build_diagnostics(
    test_data: pd.DataFrame, probabilities: np.ndarray
) -> dict[str, list[dict[str, object]]]:
    """Resume si las probabilidades se comportan bien de forma global y por segmento."""
    data = test_data.copy()
    data["probabilidad_predicha"] = probabilities
    data["bin_calibracion"] = pd.cut(
        data["probabilidad_predicha"],
        bins=np.linspace(0, 1, 6),
        include_lowest=True,
        labels=["0,0–0,2", "0,2–0,4", "0,4–0,6", "0,6–0,8", "0,8–1,0"],
    )
    calibration = _segment_summary(data, "bin_calibracion")
    return {
        "calibration": calibration,
        "by_time_band": _segment_summary(data, "franja_horaria"),
        "by_court_type": _segment_summary(data, "tipo_pista"),
    }


def _segment_summary(data: pd.DataFrame, column: str) -> list[dict[str, object]]:
    grouped = (
        data.groupby(column, observed=False)
        .agg(
            turnos=(TARGET_COLUMN, "size"),
            ocupacion_observada=(TARGET_COLUMN, "mean"),
            probabilidad_media=("probabilidad_predicha", "mean"),
        )
        .reset_index()
    )
    grouped["diferencia_absoluta"] = (
        grouped["ocupacion_observada"] - grouped["probabilidad_media"]
    ).abs()
    for column_name in ["ocupacion_observada", "probabilidad_media", "diferencia_absoluta"]:
        grouped[column_name] = grouped[column_name].round(4)
    return grouped.to_dict(orient="records")
