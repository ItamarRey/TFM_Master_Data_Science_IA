"""Compara tarifa fija y regla dinámica en el periodo de test del escenario sintético."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from padel_pricing.modeling import prepare_modeling_data, temporal_train_test_split
from padel_pricing.pricing import load_pricing_policy, recommend_price


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "gold" / "gold_slots_pistas.parquet",
        help="Ruta al dataset Gold.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "models" / "occupancy_model.joblib",
        help="Modelo de ocupación entrenado.",
    )
    parser.add_argument(
        "--test-start",
        help="Fecha de inicio del test; debe coincidir con el experimento de modelos.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists() or not args.model.exists():
        raise FileNotFoundError(
            "Falta Gold o el modelo entrenado. Ejecuta antes "
            "scripts/train_occupancy_models.py."
        )

    policy = load_pricing_policy(PROJECT_ROOT / "config" / "pricing_scenarios.json")
    model = joblib.load(args.model)
    data = prepare_modeling_data(pd.read_parquet(args.input))
    test_data = temporal_train_test_split(data, test_start=args.test_start).test
    model_input = test_data.drop(columns=["fecha_hora_inicio", "ocupado_final"])
    probabilities = model.predict_proba(model_input)[:, 1]

    results = [
        _simulate_scenario(test_data, probabilities, scenario_name, policy)
        for scenario_name in policy.scenarios
    ]
    output_dir = PROJECT_ROOT / "reports" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pricing_scenarios.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "pricing_scenarios.md").write_text(
        _build_markdown(results), encoding="utf-8"
    )
    print(f"Informe: {output_dir / 'pricing_scenarios.md'}")


def _simulate_scenario(
    data: pd.DataFrame,
    probabilities: object,
    scenario_name: str,
    policy: object,
) -> dict[str, float | str | int]:
    fixed_revenue = 0.0
    dynamic_revenue = 0.0
    fixed_occupancy = 0.0
    dynamic_occupancy = 0.0
    changed_prices = 0
    for (_, row), probability in zip(data.iterrows(), probabilities, strict=True):
        recommendation = recommend_price(
            current_price_eur=float(row["tarifa_publicada"]),
            occupancy_probability=float(probability),
            scenario_name=scenario_name,
            policy=policy,
        )
        fixed_revenue += recommendation.expected_revenue_current_eur
        dynamic_revenue += recommendation.expected_revenue_suggested_eur
        fixed_occupancy += recommendation.current_occupancy_probability
        dynamic_occupancy += recommendation.simulated_occupancy_probability
        changed_prices += int(recommendation.suggested_price_eur != recommendation.current_price_eur)

    total_slots = len(data)
    return {
        "scenario": scenario_name,
        "slots": total_slots,
        "prices_changed": changed_prices,
        "expected_occupancy_fixed": round(fixed_occupancy, 2),
        "expected_occupancy_dynamic": round(dynamic_occupancy, 2),
        "expected_revenue_fixed_eur": round(fixed_revenue, 2),
        "expected_revenue_dynamic_eur": round(dynamic_revenue, 2),
        "expected_revenue_difference_eur": round(dynamic_revenue - fixed_revenue, 2),
    }


def _build_markdown(results: list[dict[str, float | str | int]]) -> str:
    lines = [
        "# Simulación de escenarios de precio",
        "",
        "La comparación usa la probabilidad estimada por el modelo para la tarifa actual. "
        "La ocupación a otros precios se ajusta mediante elasticidades configuradas; por tanto, "
        "es un escenario simulado y no una estimación causal ni un resultado de un club real.",
        "",
        "| escenario | turnos | precios modificados | ocupación fija esperada | "
        "ocupación dinámica esperada | "
        "ingreso fijo esperado (€) | ingreso dinámico esperado (€) | diferencia (€) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        lines.append(
            "| {scenario} | {slots} | {prices_changed} | {expected_occupancy_fixed:.2f} | "
            "{expected_occupancy_dynamic:.2f} | {expected_revenue_fixed_eur:.2f} | "
            "{expected_revenue_dynamic_eur:.2f} | {expected_revenue_difference_eur:.2f} |".format(
                **item
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
