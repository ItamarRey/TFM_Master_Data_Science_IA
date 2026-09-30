from datetime import date, time

from backend.app.services import weather_service


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "hourly": {
                "time": ["2026-10-01T18:00", "2026-10-01T19:00"],
                "temperature_2m": [22.4, 21.9],
                "precipitation": [0.2, 0.0],
                "wind_speed_10m": [13.5, 12.4],
                "weather_code": [2, 1],
            }
        }


def test_fetch_turn_weather_uses_start_hour_for_half_hour_slot(monkeypatch) -> None:
    requested_params: dict[str, object] = {}

    def fake_get(url: str, params: dict[str, object], timeout: float) -> FakeResponse:
        requested_params.update(params)
        return FakeResponse()

    monkeypatch.setattr(weather_service.httpx, "get", fake_get)

    forecast = weather_service.fetch_turn_weather(date(2026, 10, 1), time(18, 30))

    assert forecast.weather_time == time(18, 0)
    assert forecast.temperature_c == 22.4
    assert forecast.precipitation_mm == 0.2
    assert forecast.condition == "Poco nuboso"
    assert requested_params["timezone"] == "Atlantic/Canary"


def test_simulated_weather_is_clearly_identified() -> None:
    forecast = weather_service.simulated_turn_weather(
        date(2026, 10, 1), time(20, 0), 24.0, 1.5, 18.0
    )

    assert forecast.is_simulation
    assert forecast.source == "manual_simulation"
    assert forecast.as_response().source_label == "Simulación manual"
