"""Entrena y compara modelos de ocupación sobre Gold con división temporal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from padel_pricing.modeling import (
    prepare_modeling_data,
    run_experiment,
    select_deployable_model,
    temporal_train_test_split,
)
from padel_pricing.modeling.experiment import experiment_metadata


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
        "--test-start",
        help="Fecha de inicio del test (ISO 8601). Por defecto, un año después del primer turno.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(
            f"No existe {args.input}. Ejecuta antes scripts/generate_synthetic_data.py."
        )

    gold_data = pd.read_parquet(args.input)
    data = prepare_modeling_data(gold_data)
    split = temporal_train_test_split(data, test_start=args.test_start)
    result = run_experiment(split.train, split.test, seed=42)
    metadata = experiment_metadata(result, split.test_start)
    selected_name = select_deployable_model(result.metrics)

    models_dir = PROJECT_ROOT / "models"
    reports_dir = PROJECT_ROOT / "reports" / "generated"
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(result.models[selected_name], models_dir / "occupancy_model.joblib")
    (models_dir / "occupancy_model_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    result.test_predictions.to_parquet(reports_dir / "occupancy_test_predictions.parquet", index=False)
    _write_markdown_report(metadata, len(split.train), len(split.test), reports_dir)

    print(f"Entrenamiento: {len(split.train):,} turnos | Test: {len(split.test):,} turnos")
    print(f"Modelo seleccionado: {selected_name}")
    print(f"Artefacto: {models_dir / 'occupancy_model.joblib'}")
    print(f"Informe: {reports_dir / 'model_comparison.md'}")


def _write_markdown_report(
    metadata: dict[str, object], train_rows: int, test_rows: int, output_dir: Path
) -> None:
    metrics = metadata["metrics"]
    assert isinstance(metrics, dict)
    lines = [
        "# Comparativa de modelos de ocupación",
        "",
        "## Diseño experimental",
        "",
        f"- Entrenamiento: **{train_rows:,}** turnos anteriores a {metadata['test_start'][:10]}.",
        f"- Test temporal: **{test_rows:,}** turnos posteriores o iguales a esa fecha.",
        "- Target: `ocupado_final`; se excluyen los turnos bloqueados.",
        "- Entradas: variables conocidas 48 h antes. No se usan cancelaciones, ingresos, estados finales ni meteorología observada.",
        "- La selección se realiza por menor Brier score, porque el producto necesita probabilidades bien calibradas.",
        "",
        "## Resultados en test",
        "",
        "| modelo | ROC-AUC | AP | Brier | Log loss | Accuracy (0,5) | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model_name, values in metrics.items():
        assert isinstance(values, dict)
        lines.append(
            "| {name} | {roc_auc:.4f} | {average_precision:.4f} | {brier_score:.4f} | "
            "{log_loss:.4f} | {accuracy_at_0_5:.4f} | {precision_at_0_5:.4f} | "
            "{recall_at_0_5:.4f} | {f1_at_0_5:.4f} |".format(name=model_name, **values)
        )
    lines.extend(
        [
            "",
            "## Modelo seleccionado",
            "",
            f"`{metadata['selected_model']}`. Los resultados se refieren exclusivamente al escenario sintético configurado y no prueban impacto económico en un club real.",
        ]
    )
    (output_dir / "model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
