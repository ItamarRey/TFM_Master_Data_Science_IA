from backend.app.api.routes import predictions
from backend.app.schemas.prediction import PredictionRequest


def test_prediction_endpoint_returns_recommendation(monkeypatch) -> None:
    monkeypatch.setattr(
        predictions,
        "predict_turn",
        lambda request: {
            "occupancy_probability": 0.42,
            "current_price": 12.0,
            "suggested_price": 12.0,
            "variation_pct": 0.0,
            "scenario": "medium",
            "scenario_label": "Sensibilidad media",
            "simulated_occupancy_probability": 0.42,
            "expected_revenue_current": 5.04,
            "expected_revenue_suggested": 5.04,
            "candidates": [
                {
                    "price_eur": 12.0,
                    "variation_pct": 0.0,
                    "simulated_occupancy_probability": 0.42,
                    "simulated_expected_revenue_eur": 5.04,
                }
            ],
            "weather": {
                "date": "2026-09-27",
                "start_time": "18:30:00",
                "weather_time": "18:00:00",
                "temperature_c": 22.0,
                "precipitation_mm": 0.0,
                "wind_kmh": 15.0,
                "condition": "Despejado",
                "source": "open-meteo",
                "source_label": "Open-Meteo · previsión automática",
                "is_simulation": False,
            },
            "explanation": ["La demanda estimada se encuentra en un rango intermedio."],
            "warning": "Datos sintéticos · La recomendación requiere revisión.",
        },
    )

    request = PredictionRequest(
        date="2026-09-27",
        court_id="exterior_1",
        start_time="18:30",
        current_price=12.0,
        scenario="medium",
        weather_mode="automatic",
    )
    response = predictions.create_prediction(request)

    assert response.suggested_price == 12.0
    assert response.weather.source == "open-meteo"
