"""Persistencia local de decisiones simuladas para el recorrido del MVP."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.app.schemas.decision import DecisionRequest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DECISION_LOG_PATH = PROJECT_ROOT / "data" / "app" / "decisions.jsonl"
ACTION_LABELS = {
    "apply_suggested": "Tarifa sugerida aplicada",
    "keep_base": "Tarifa base mantenida",
}


def record_decision(request: DecisionRequest) -> dict[str, object]:
    """Guarda una decisión local; no modifica ninguna tarifa operativa real."""
    created_at = datetime.now(UTC)
    record = {
        **request.model_dump(mode="json"),
        "id": str(uuid4()),
        "created_at": created_at.isoformat(),
        "action_label": ACTION_LABELS[request.action],
    }
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECISION_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def list_decisions(limit: int = 20) -> list[dict[str, object]]:
    """Recupera las últimas decisiones simuladas, primero las más recientes."""
    if not DECISION_LOG_PATH.exists():
        return []
    with DECISION_LOG_PATH.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]
    return list(reversed(records[-limit:]))
