"""Genera y guarda el dataset sintético reproducible del MVP."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from padel_pricing.simulation import (
    fetch_weather,
    generate_operational_data,
    load_simulation_config,
)
from padel_pricing.data_quality import (
    build_gold_dataset,
    clean_operational_data,
    inject_controlled_issues,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "simulation_config.json",
        help="Ruta al archivo JSON de configuración.",
    )
    parser.add_argument(
        "--weather-source",
        choices=["open-meteo", "synthetic"],
        help="Sobrescribe la fuente meteorológica configurada.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_simulation_config(args.config)
    if args.weather_source:
        config = replace(config, weather=replace(config.weather, source=args.weather_source))

    raw_dir = PROJECT_ROOT / "data" / "raw"
    processed_dir = PROJECT_ROOT / "data" / "processed"
    gold_dir = PROJECT_ROOT / "data" / "gold"
    for directory in (raw_dir, processed_dir, gold_dir):
        directory.mkdir(parents=True, exist_ok=True)

    weather = fetch_weather(config)
    operational_truth = generate_operational_data(config, weather)
    raw_operational, injected_issues = inject_controlled_issues(operational_truth, config)
    silver_operational, quality_report = clean_operational_data(raw_operational)
    gold_data = build_gold_dataset(silver_operational, config)

    weather.to_json(raw_dir / "weather_hourly.json", orient="records", date_format="iso")
    weather.to_parquet(processed_dir / "weather_hourly.parquet", index=False)
    raw_operational.to_csv(raw_dir / "operational_slots_raw.csv", index=False)
    silver_operational.to_parquet(processed_dir / "silver_slots_pistas.parquet", index=False)
    gold_data.to_parquet(gold_dir / "gold_slots_pistas.parquet", index=False)
    (processed_dir / "operational_quality_report.json").write_text(
        json.dumps(
            {"injected_issues": injected_issues, "cleaning_result": quality_report},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    metadata = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(gold_data),
        "raw_operational_rows": len(raw_operational),
        "seed": config.seed,
        "weather_source": config.weather.source,
        "configuration": asdict(config),
        "definitions": {
            "ocupado_final": (
                "Reserva confirmada y no cancelada; un no-show sigue bloqueando el turno."
            ),
            "forecast": (
                "Meteorología real con un error simulado que representa la información "
                "disponible 48 h antes."
            ),
            "raw_quality_issues": (
                "Incidencias sintéticas pequeñas, reproducibles y documentadas, "
                "inyectadas solo para validar la capa Silver."
            ),
        },
        "data_quality": quality_report,
    }
    (gold_dir / "gold_slots_pistas_metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )

    occupied = gold_data.loc[~gold_data["bloqueado"], "ocupado_final"].mean()
    print(f"Extracto Raw operativo: {len(raw_operational):,} filas")
    print(f"Capa Silver: {len(silver_operational):,} turnos | Duplicados eliminados: {quality_report['duplicate_rows_removed']}")
    print(f"Dataset Gold: {len(gold_data):,} turnos")
    print(f"Ocupación final en turnos elegibles: {occupied:.1%}")
    print(f"Informe de calidad: {processed_dir / 'operational_quality_report.json'}")


if __name__ == "__main__":
    main()
