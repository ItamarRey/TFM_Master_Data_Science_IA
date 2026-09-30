import pandas as pd

from padel_pricing.modeling.dataset import (
    MODEL_FEATURES,
    prepare_modeling_data,
    temporal_train_test_split,
)
from padel_pricing.modeling.experiment import historical_baseline_probabilities


def _gold_like_data() -> pd.DataFrame:
    rows = []
    for index, timestamp in enumerate(
        pd.to_datetime(
            ["2024-01-01 18:00", "2024-01-02 18:00", "2024-01-03 18:00", "2024-01-04 18:00"]
        )
    ):
        rows.append(
            {
                "fecha_hora_inicio": timestamp,
                "id_pista": "exterior_1",
                "tipo_pista": "exterior",
                "dia_semana": "Monday",
                "mes": 1,
                "es_fin_de_semana": False,
                "es_festivo": False,
                "franja_horaria": "tarde",
                "pronostico_temperatura_c_imputado": False,
                "pronostico_precipitacion_mm_imputado": False,
                "pronostico_viento_kmh_imputado": False,
                "tarifa_publicada": 14.0,
                "pronostico_temperatura_c": 22.0,
                "pronostico_precipitacion_mm": 0.0,
                "pronostico_viento_kmh": 12.0,
                "ocupado_final": index % 2,
                "bloqueado": index == 3,
                "cancelado": False,
                "ingreso_final": 0.0,
            }
        )
    return pd.DataFrame(rows)


def test_prepare_data_excludes_blocked_and_outcome_columns() -> None:
    data = prepare_modeling_data(_gold_like_data())

    assert len(data) == 3
    assert set(data.columns) == {"fecha_hora_inicio", "ocupado_final", *MODEL_FEATURES}
    assert "cancelado" not in data.columns
    assert "ingreso_final" not in data.columns


def test_temporal_split_and_baseline_only_use_the_past() -> None:
    prepared = prepare_modeling_data(_gold_like_data())
    split = temporal_train_test_split(prepared, test_start="2024-01-03")

    probabilities = historical_baseline_probabilities(split.train, split.test)

    assert len(split.train) == 2
    assert len(split.test) == 1
    assert probabilities.tolist() == [0.5]


def test_prediction_time_features_are_available_without_outcomes() -> None:
    prepared = prepare_modeling_data(_gold_like_data())

    first_row = prepared.iloc[0]
    assert first_row["hora_inicio"] == 18
    assert first_row["es_hora_punta"]
    assert first_row["precipitacion_exterior"] == 0.0
