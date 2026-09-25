"""Regla transparente de recomendación de tarifas por escenarios."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PricingScenario:
    name: str
    label: str
    elasticity: float


@dataclass(frozen=True)
class PricingPolicy:
    minimum_price_eur: float
    maximum_price_eur: float
    low_demand_probability_threshold: float
    high_demand_probability_threshold: float
    candidate_variations: tuple[float, ...]
    scenarios: dict[str, PricingScenario]


@dataclass(frozen=True)
class PriceCandidate:
    price_eur: float
    variation_pct: float
    simulated_occupancy_probability: float
    simulated_expected_revenue_eur: float
    is_allowed: bool


@dataclass(frozen=True)
class PricingRecommendation:
    scenario: str
    scenario_label: str
    current_price_eur: float
    suggested_price_eur: float
    variation_pct: float
    current_occupancy_probability: float
    simulated_occupancy_probability: float
    expected_revenue_current_eur: float
    expected_revenue_suggested_eur: float
    candidates: tuple[PriceCandidate, ...]
    explanation: str

    def to_dict(self) -> dict[str, object]:
        """Convierte el resultado a un formato apropiado para API o informe."""
        return asdict(self)


def load_pricing_policy(path: Path) -> PricingPolicy:
    """Carga los límites y supuestos explícitos de la regla de tarifa."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = payload["rules"]
    scenarios = {
        name: PricingScenario(
            name=name,
            label=values["label"],
            elasticity=float(values["elasticity"]),
        )
        for name, values in payload["scenarios"].items()
    }
    policy = PricingPolicy(
        minimum_price_eur=float(rules["minimum_price_eur"]),
        maximum_price_eur=float(rules["maximum_price_eur"]),
        low_demand_probability_threshold=float(rules["low_demand_probability_threshold"]),
        high_demand_probability_threshold=float(rules["high_demand_probability_threshold"]),
        candidate_variations=tuple(float(value) for value in rules["candidate_variations"]),
        scenarios=scenarios,
    )
    _validate_policy(policy)
    return policy


def recommend_price(
    *,
    current_price_eur: float,
    occupancy_probability: float,
    scenario_name: str,
    policy: PricingPolicy,
) -> PricingRecommendation:
    """Elige la mejor tarifa entre opciones acotadas según un escenario supuesto.

    La probabilidad inicial procede del modelo para la tarifa actual. Cada precio
    candidato ajusta esa probabilidad con una elasticidad *supuesto*; no se
    interpreta como estimación causal observada en un club real.
    """
    _validate_recommendation_inputs(
        current_price_eur=current_price_eur,
        occupancy_probability=occupancy_probability,
        scenario_name=scenario_name,
        policy=policy,
    )
    scenario = policy.scenarios[scenario_name]
    eligible_variations = _variations_for_demand(occupancy_probability, policy)
    candidates = tuple(
        _build_candidate(
            current_price_eur=current_price_eur,
            current_probability=occupancy_probability,
            variation=variation,
            elasticity=scenario.elasticity,
            policy=policy,
            is_allowed=variation in eligible_variations,
        )
        for variation in policy.candidate_variations
    )
    unique_candidates = _unique_candidates(candidates)
    allowed_candidates = tuple(candidate for candidate in unique_candidates if candidate.is_allowed)
    current_candidate = next(
        candidate for candidate in unique_candidates if candidate.variation_pct == 0.0
    )
    # En caso de empate se conserva el precio actual para evitar cambios sin beneficio esperado.
    selected = max(
        allowed_candidates,
        key=lambda candidate: (
            candidate.simulated_expected_revenue_eur,
            candidate.price_eur == current_price_eur,
        ),
    )
    return PricingRecommendation(
        scenario=scenario.name,
        scenario_label=scenario.label,
        current_price_eur=round(current_price_eur, 2),
        suggested_price_eur=selected.price_eur,
        variation_pct=selected.variation_pct,
        current_occupancy_probability=round(occupancy_probability, 4),
        simulated_occupancy_probability=selected.simulated_occupancy_probability,
        expected_revenue_current_eur=current_candidate.simulated_expected_revenue_eur,
        expected_revenue_suggested_eur=selected.simulated_expected_revenue_eur,
        candidates=unique_candidates,
        explanation=_explanation(selected, current_candidate, scenario),
    )


def _build_candidate(
    *,
    current_price_eur: float,
    current_probability: float,
    variation: float,
    elasticity: float,
    policy: PricingPolicy,
    is_allowed: bool,
) -> PriceCandidate:
    candidate_price = min(
        max(round(current_price_eur * (1 + variation), 2), policy.minimum_price_eur),
        policy.maximum_price_eur,
    )
    actual_variation = round(candidate_price / current_price_eur - 1, 4)
    probability = _scenario_probability(
        current_probability=current_probability,
        current_price=current_price_eur,
        candidate_price=candidate_price,
        elasticity=elasticity,
    )
    return PriceCandidate(
        price_eur=candidate_price,
        variation_pct=actual_variation,
        simulated_occupancy_probability=probability,
        simulated_expected_revenue_eur=round(candidate_price * probability, 4),
        is_allowed=is_allowed,
    )


def _scenario_probability(
    *, current_probability: float, current_price: float, candidate_price: float, elasticity: float
) -> float:
    adjusted = current_probability * (candidate_price / current_price) ** (-elasticity)
    return round(min(max(adjusted, 0.001), 0.999), 4)


def _unique_candidates(candidates: tuple[PriceCandidate, ...]) -> tuple[PriceCandidate, ...]:
    unique: dict[float, PriceCandidate] = {}
    for candidate in candidates:
        previous = unique.get(candidate.price_eur)
        if previous is None or candidate.is_allowed:
            unique[candidate.price_eur] = candidate
    return tuple(sorted(unique.values(), key=lambda candidate: candidate.price_eur))


def _variations_for_demand(probability: float, policy: PricingPolicy) -> tuple[float, ...]:
    """Evita subir en valle o bajar en alta demanda solo por la elasticidad asumida."""
    if probability < policy.low_demand_probability_threshold:
        return tuple(value for value in policy.candidate_variations if value <= 0)
    if probability > policy.high_demand_probability_threshold:
        return tuple(value for value in policy.candidate_variations if value >= 0)
    return (0.0,)


def _explanation(
    selected: PriceCandidate, current: PriceCandidate, scenario: PricingScenario
) -> str:
    if selected.price_eur == current.price_eur:
        return (
            f"Con {scenario.label.lower()}, mantener la tarifa actual maximiza el ingreso "
            "esperado dentro del rango permitido."
        )
    direction = "subir" if selected.price_eur > current.price_eur else "bajar"
    return (
        f"El escenario de {scenario.label.lower()} sugiere {direction} la tarifa porque "
        "mejora el ingreso esperado simulado dentro del rango permitido."
    )


def _validate_policy(policy: PricingPolicy) -> None:
    if policy.minimum_price_eur <= 0 or policy.maximum_price_eur < policy.minimum_price_eur:
        raise ValueError("Los límites de precio configurados no son válidos.")
    if not (
        0 < policy.low_demand_probability_threshold < policy.high_demand_probability_threshold < 1
    ):
        raise ValueError("Los umbrales de probabilidad de demanda no son válidos.")
    if 0.0 not in policy.candidate_variations:
        raise ValueError("candidate_variations debe incluir 0.0 para evaluar mantener la tarifa.")
    if any(abs(value) > 0.10 for value in policy.candidate_variations):
        raise ValueError("La regla no puede proponer variaciones superiores al ±10%.")
    if not policy.scenarios or any(item.elasticity <= 0 for item in policy.scenarios.values()):
        raise ValueError("Cada escenario debe tener una elasticidad positiva.")


def _validate_recommendation_inputs(
    *, current_price_eur: float,
    occupancy_probability: float,
    scenario_name: str,
    policy: PricingPolicy,
) -> None:
    if current_price_eur <= 0:
        raise ValueError("current_price_eur debe ser positivo.")
    if not policy.minimum_price_eur <= current_price_eur <= policy.maximum_price_eur:
        raise ValueError("current_price_eur debe estar dentro de los límites configurados.")
    if not 0 <= occupancy_probability <= 1:
        raise ValueError("occupancy_probability debe estar entre 0 y 1.")
    if scenario_name not in policy.scenarios:
        raise ValueError(f"Escenario no configurado: {scenario_name}")
