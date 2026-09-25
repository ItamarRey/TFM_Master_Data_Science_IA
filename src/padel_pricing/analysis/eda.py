"""Análisis reproducible del dataset Gold antes del entrenamiento."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_LABELS = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}


def analyze_dataset(data: pd.DataFrame) -> dict[str, Any]:
    """Calcula controles y métricas sin modificar el dataset de entrada."""
    _require_columns(data)
    quality = _quality_checks(data)
    if not quality["passed"]:
        raise ValueError(f"El dataset no supera los controles: {quality['failures']}")

    eligible = data.loc[~data["bloqueado"]].copy()
    eligible["categoria_lluvia"] = _rain_category(eligible["precipitacion_mm"])
    eligible["dia_semana_es"] = eligible["dia_semana"].map(DAY_LABELS).fillna(
        eligible["dia_semana"]
    )

    result = {
        "quality": quality,
        "summary": _summary(data, eligible),
        "occupancy_by_time_band": _group_metrics(eligible, ["franja_horaria"]),
        "occupancy_by_day": _group_metrics(eligible, ["dia_semana", "dia_semana_es"]),
        "occupancy_by_court_type": _group_metrics(eligible, ["tipo_pista"]),
        "occupancy_by_court": _group_metrics(eligible, ["id_pista", "tipo_pista"]),
        "occupancy_by_month": _group_metrics(eligible, ["mes"]),
        "exterior_weather_impact": _group_metrics(
            eligible.loc[eligible["tipo_pista"] == "exterior"], ["categoria_lluvia"]
        ),
        "revenue_by_time_band": _revenue_by_time_band(eligible),
    }
    return result


def write_analysis_artifacts(analysis: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Guarda un informe Markdown legible y métricas JSON reutilizables por el frontend."""
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "eda_summary.md"
    json_path = output_dir / "eda_metrics.json"

    markdown_path.write_text(_build_markdown(analysis), encoding="utf-8")
    json_path.write_text(
        json.dumps(_serialise_analysis(analysis), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return markdown_path, json_path


def _require_columns(data: pd.DataFrame) -> None:
    required = {
        "id_slot",
        "bloqueado",
        "cancelado",
        "ocupado_final",
        "estado_reserva",
        "franja_horaria",
        "dia_semana",
        "tipo_pista",
        "id_pista",
        "mes",
        "precipitacion_mm",
        "tarifa_publicada",
        "ingreso_final",
    }
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Faltan columnas necesarias para el análisis: {', '.join(missing)}")


def _quality_checks(data: pd.DataFrame) -> dict[str, Any]:
    missing_values = {column: int(count) for column, count in data.isna().sum().items() if count}
    invalid_blocked = int(data.loc[data["bloqueado"], "ocupado_final"].sum())
    invalid_cancelled = int(data.loc[data["cancelado"], "ocupado_final"].sum())
    invalid_prices = int((data["tarifa_publicada"] <= 0).sum())
    failures = []
    if not data["id_slot"].is_unique:
        failures.append("id_slot contiene duplicados")
    if invalid_blocked:
        failures.append("hay turnos bloqueados marcados como ocupados")
    if invalid_cancelled:
        failures.append("hay reservas canceladas marcadas como ocupadas")
    if invalid_prices:
        failures.append("hay tarifas publicadas no positivas")

    return {
        "passed": not failures,
        "failures": failures,
        "rows": int(len(data)),
        "duplicate_slots": int(data["id_slot"].duplicated().sum()),
        "missing_values": missing_values,
        "blocked_and_occupied": invalid_blocked,
        "cancelled_and_occupied": invalid_cancelled,
        "non_positive_prices": invalid_prices,
    }


def _summary(data: pd.DataFrame, eligible: pd.DataFrame) -> dict[str, Any]:
    return {
        "turnos_totales": int(len(data)),
        "turnos_bloqueados": int(data["bloqueado"].sum()),
        "turnos_elegibles": int(len(eligible)),
        "ocupacion_final_pct": round(float(eligible["ocupado_final"].mean() * 100), 2),
        "cancelaciones_pct": round(
            float(data.loc[~data["bloqueado"], "cancelado"].mean() * 100), 2
        ),
        "no_shows": int(data["no_show"].sum()) if "no_show" in data else None,
        "ingresos_finales_eur": round(float(data["ingreso_final"].sum()), 2),
    }


def _group_metrics(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=[*columns, "turnos", "ocupacion_pct", "tarifa_media_eur"])
    result = (
        data.groupby(columns, dropna=False)
        .agg(
            turnos=("id_slot", "size"),
            ocupacion_pct=("ocupado_final", lambda value: round(float(value.mean() * 100), 2)),
            tarifa_media_eur=("tarifa_publicada", "mean"),
        )
        .reset_index()
    )
    result["tarifa_media_eur"] = result["tarifa_media_eur"].round(2)
    if columns == ["dia_semana", "dia_semana_es"]:
        order = {day: index for index, day in enumerate(DAY_ORDER)}
        result["orden"] = result["dia_semana"].map(order)
        result = result.sort_values("orden").drop(columns="orden")
    return result


def _revenue_by_time_band(data: pd.DataFrame) -> pd.DataFrame:
    result = (
        data.groupby("franja_horaria")
        .agg(
            turnos=("id_slot", "size"),
            reservas_confirmadas=("ocupado_final", "sum"),
            ingresos_eur=("ingreso_final", "sum"),
        )
        .reset_index()
    )
    result["ingresos_eur"] = result["ingresos_eur"].round(2)
    return result


def _rain_category(precipitation: pd.Series) -> pd.Series:
    return pd.cut(
        precipitation,
        bins=[-0.01, 0.0, 1.0, float("inf")],
        labels=["Sin lluvia", "Lluvia ligera", "Lluvia moderada o alta"],
    ).astype(str)


def _build_markdown(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    quality = analysis["quality"]
    sections = [
        "# Informe de análisis exploratorio",
        "",
        "## Control de calidad",
        "",
        f"- Controles superados: **{'sí' if quality['passed'] else 'no'}**.",
        f"- Filas analizadas: **{quality['rows']:,}**.",
        f"- Slots duplicados: **{quality['duplicate_slots']}**.",
        f"- Turnos bloqueados y ocupados: **{quality['blocked_and_occupied']}**.",
        f"- Cancelaciones marcadas como ocupadas: **{quality['cancelled_and_occupied']}**.",
        "",
        "## Resumen general",
        "",
        f"- Turnos ofertados: **{summary['turnos_totales']:,}**.",
        f"- Turnos bloqueados: **{summary['turnos_bloqueados']:,}**.",
        f"- Ocupación final de turnos elegibles: **{summary['ocupacion_final_pct']:.2f}%**.",
        f"- Cancelaciones: **{summary['cancelaciones_pct']:.2f}%**.",
        f"- Ingresos finales simulados: **{summary['ingresos_finales_eur']:,.2f} €**.",
        "",
        "## Ocupación por franja horaria",
        "",
        _dataframe_to_markdown(analysis["occupancy_by_time_band"]),
        "",
        "## Ocupación por día de la semana",
        "",
        _dataframe_to_markdown(analysis["occupancy_by_day"].drop(columns="dia_semana")),
        "",
        "## Ocupación por tipo de pista",
        "",
        _dataframe_to_markdown(analysis["occupancy_by_court_type"]),
        "",
        "## Efecto de la lluvia en pistas exteriores",
        "",
        _dataframe_to_markdown(analysis["exterior_weather_impact"]),
        "",
        "## Ingresos por franja horaria",
        "",
        _dataframe_to_markdown(analysis["revenue_by_time_band"]),
        "",
        "## Nota metodológica",
        "",
        "Las reservas, los precios y la respuesta de la ocupación son sintéticos. "
        "La meteorología procede de la fuente configurada. Este informe valida la coherencia "
        "interna del escenario; no estima el rendimiento de un club real.",
    ]
    return "\n".join(sections) + "\n"


def _dataframe_to_markdown(data: pd.DataFrame) -> str:
    columns = list(data.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for row in data.itertuples(index=False, name=None):
        cells = [str(value) for value in row]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, divider, *rows])


def _serialise_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in analysis.items():
        result[key] = value.to_dict(orient="records") if isinstance(value, pd.DataFrame) else value
    return result
