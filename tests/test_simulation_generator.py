from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from padel_pricing.simulation import (
    fetch_weather,
    generate_operational_data,
    load_simulation_config,
)


def _small_config():
    base = load_simulation_config(Path("config/simulation_config.json"))
    return replace(
        base,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        weather=replace(base.weather, source="synthetic"),
    )


def test_generator_is_reproducible() -> None:
    config = _small_config()

    first = generate_operational_data(config, fetch_weather(config))
    second = generate_operational_data(config, fetch_weather(config))

    pd.testing.assert_frame_equal(first, second)


def test_generator_respects_slot_contract() -> None:
    config = _small_config()
    data = generate_operational_data(config, fetch_weather(config))

    assert len(data) == config.expected_slots
    assert data["id_slot"].is_unique
    assert not data.loc[data["bloqueado"], "ocupado_final"].any()
    assert {"interior", "exterior"} == set(data["tipo_pista"])
