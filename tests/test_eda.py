import pandas as pd

from padel_pricing.analysis import analyze_dataset


def _valid_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id_slot": ["a", "b", "c"],
            "bloqueado": [False, False, True],
            "cancelado": [False, True, False],
            "ocupado_final": [1, 0, 0],
            "estado_reserva": ["confirmado", "cancelado", "bloqueado"],
            "franja_horaria": ["noche", "mañana", "noche"],
            "dia_semana": ["Monday", "Monday", "Tuesday"],
            "tipo_pista": ["exterior", "interior", "exterior"],
            "id_pista": ["exterior_1", "interior_1", "exterior_1"],
            "mes": [1, 1, 1],
            "precipitacion_mm": [0.0, 0.5, 0.0],
            "tarifa_publicada": [12.0, 12.0, 12.0],
            "ingreso_final": [12.0, 0.0, 0.0],
        }
    )


def test_analysis_returns_expected_summary() -> None:
    analysis = analyze_dataset(_valid_dataset())

    assert analysis["quality"]["passed"]
    assert analysis["summary"]["turnos_elegibles"] == 2
    assert analysis["summary"]["ocupacion_final_pct"] == 50.0


def test_analysis_rejects_blocked_occupied_slot() -> None:
    data = _valid_dataset()
    data.loc[2, "ocupado_final"] = 1

    try:
        analyze_dataset(data)
    except ValueError as exc:
        assert "bloqueados" in str(exc)
    else:
        raise AssertionError("Se esperaba un error de calidad")
