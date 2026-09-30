"""Persistencia local de decisiones simuladas para el recorrido del MVP."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from backend.app.schemas.decision import DecisionRequest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DECISION_LOG_PATH = PROJECT_ROOT / "data" / "app" / "decisions.jsonl"
SIMULATED_TARIFFS_PATH = PROJECT_ROOT / "data" / "app" / "simulated_tariffs.json"
ACTION_LABELS = {
    "apply_suggested": "Tarifa sugerida aplicada",
    "keep_base": "Tarifa base mantenida",
}


def record_decision(request: DecisionRequest) -> dict[str, object]:
    """Guarda una decisión y actualiza una tarifa únicamente dentro de la simulación."""
    created_at = datetime.now(UTC)
    applied_price = (
        request.suggested_price if request.action == "apply_suggested" else request.current_price
    )
    record = {
        **request.model_dump(mode="json"),
        "id": str(uuid4()),
        "created_at": created_at.isoformat(),
        "action_label": ACTION_LABELS[request.action],
        "applied_price_eur": applied_price,
    }
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECISION_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    _upsert_simulated_tariff(record)
    return record


def list_decisions(limit: int = 20) -> list[dict[str, object]]:
    """Recupera las últimas decisiones simuladas, primero las más recientes."""
    if not DECISION_LOG_PATH.exists():
        return []
    with DECISION_LOG_PATH.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]
    return list(reversed(records[-limit:]))


def list_simulated_tariffs(selected_date: date | None = None) -> list[dict[str, object]]:
    """Devuelve las tarifas activas, una por cada fecha, pista y hora."""
    if not SIMULATED_TARIFFS_PATH.exists():
        return []
    records = json.loads(SIMULATED_TARIFFS_PATH.read_text(encoding="utf-8"))
    if selected_date:
        records = [record for record in records if record["date"] == selected_date.isoformat()]
    return sorted(
        records,
        key=lambda record: (record["date"], record["start_time"], record["court_id"]),
    )


def _upsert_simulated_tariff(decision: dict[str, object]) -> None:
    """Mantiene la última tarifa de cada turno sin tocar ningún sistema externo."""
    SIMULATED_TARIFFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = list_simulated_tariffs()
    record = {
        "date": decision["date"],
        "court_id": decision["court_id"],
        "start_time": decision["start_time"],
        "price_eur": decision["applied_price_eur"],
        "scenario": decision["scenario"],
        "action": decision["action"],
        "action_label": decision["action_label"],
        "updated_at": decision["created_at"],
        "decision_id": decision["id"],
    }
    key = (record["date"], record["court_id"], record["start_time"])
    updated = [
        item for item in existing if (item["date"], item["court_id"], item["start_time"]) != key
    ]
    updated.append(record)
    SIMULATED_TARIFFS_PATH.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8"
    )
