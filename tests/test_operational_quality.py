from dataclasses import replace
from datetime import date
from pathlib import Path

from padel_pricing.data_quality import (
    build_gold_dataset,
    clean_operational_data,
    inject_controlled_issues,
)
from padel_pricing.simulation import (
    fetch_weather,
    generate_operational_data,
    load_simulation_config,
)


def _quality_config():
    base = load_simulation_config(Path("config/simulation_config.json"))
    return replace(
        base,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        weather=replace(base.weather, source="synthetic"),
        data_quality=replace(
            base.data_quality,
            duplicate_rate=0.10,
            date_format_issue_rate=0.10,
            price_format_issue_rate=0.10,
            category_format_issue_rate=0.10,
            forecast_missing_rate=0.10,
        ),
    )


def test_raw_issues_are_cleaned_before_gold() -> None:
    config = _quality_config()
    truth = generate_operational_data(config, fetch_weather(config))

    raw, injected = inject_controlled_issues(truth, config)
    silver, report = clean_operational_data(raw)
    gold = build_gold_dataset(silver, config)

    assert len(raw) > len(truth)
    assert len(gold) == config.expected_slots
    assert gold["id_slot"].is_unique
    assert report["duplicate_rows_removed"] == injected["rows_added_as_duplicates"]
    assert report["datetime_formats_normalised"] == injected["date_format_issues"]
    assert report["price_formats_normalised"] == injected["price_format_issues"]
    assert gold.filter(regex="_imputado$").any().any()


def test_cleaning_normalises_the_operational_categories() -> None:
    config = _quality_config()
    truth = generate_operational_data(config, fetch_weather(config))
    raw, _ = inject_controlled_issues(truth, config)

    silver, _ = clean_operational_data(raw)

    assert set(silver["tipo_pista"]) == {"interior", "exterior"}
    assert not silver["id_pista"].str.contains(r"^ | $", regex=True).any()
    assert silver["tarifa_publicada"].dtype.kind == "f"
