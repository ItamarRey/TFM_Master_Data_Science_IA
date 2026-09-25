"""Ejecuta controles de calidad y análisis exploratorio sobre el dataset Gold."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from padel_pricing.analysis import analyze_dataset, write_analysis_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "gold" / "gold_slots_pistas.parquet",
        help="Ruta al dataset Gold en formato Parquet.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "reports" / "generated",
        help="Carpeta donde se escribirán el informe y las métricas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(
            f"No existe {args.input}. Ejecuta antes scripts/generate_synthetic_data.py."
        )

    data = pd.read_parquet(args.input)
    analysis = analyze_dataset(data)
    markdown_path, json_path = write_analysis_artifacts(analysis, args.output_dir)

    summary = analysis["summary"]
    print("Controles de calidad superados.")
    print(f"Ocupación final de turnos elegibles: {summary['ocupacion_final_pct']:.2f}%")
    print(f"Ingresos finales simulados: {summary['ingresos_finales_eur']:,.2f} €")
    print(f"Informe Markdown: {markdown_path}")
    print(f"Métricas JSON: {json_path}")


if __name__ == "__main__":
    main()
