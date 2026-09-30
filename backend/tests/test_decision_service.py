from datetime import date, time

from backend.app.schemas.decision import DecisionRequest
from backend.app.services import decision_service


def _request(action: str, current_price: float, suggested_price: float) -> DecisionRequest:
    return DecisionRequest(
        action=action,
        date=date(2026, 10, 1),
        court_id="exterior_1",
        start_time=time(20, 0),
        scenario="medium",
        occupancy_probability=0.62,
        current_price=current_price,
        suggested_price=suggested_price,
    )


def test_decision_creates_and_updates_simulated_tariff(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(decision_service, "DECISION_LOG_PATH", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(decision_service, "SIMULATED_TARIFFS_PATH", tmp_path / "tariffs.json")

    applied = decision_service.record_decision(_request("apply_suggested", 20.0, 22.0))
    kept = decision_service.record_decision(_request("keep_base", 19.0, 21.0))
    tariffs = decision_service.list_simulated_tariffs()

    assert applied["applied_price_eur"] == 22.0
    assert kept["applied_price_eur"] == 19.0
    assert len(tariffs) == 1
    assert tariffs[0]["price_eur"] == 19.0
    assert tariffs[0]["action"] == "keep_base"
