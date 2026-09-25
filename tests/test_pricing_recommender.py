from pathlib import Path

from padel_pricing.pricing import load_pricing_policy, recommend_price


POLICY = load_pricing_policy(Path("config/pricing_scenarios.json"))


def test_low_sensitivity_can_increase_price_when_demand_is_high() -> None:
    recommendation = recommend_price(
        current_price_eur=12.0,
        occupancy_probability=0.80,
        scenario_name="low",
        policy=POLICY,
    )

    assert recommendation.suggested_price_eur == 13.2
    assert (
        recommendation.expected_revenue_suggested_eur
        > recommendation.expected_revenue_current_eur
    )


def test_high_sensitivity_can_discount_price_when_demand_is_low() -> None:
    recommendation = recommend_price(
        current_price_eur=12.0,
        occupancy_probability=0.25,
        scenario_name="high",
        policy=POLICY,
    )

    assert recommendation.suggested_price_eur == 10.8
    assert recommendation.variation_pct == -0.1


def test_recommendation_never_exceeds_policy_price_bounds() -> None:
    recommendation = recommend_price(
        current_price_eur=19.5,
        occupancy_probability=0.90,
        scenario_name="low",
        policy=POLICY,
    )

    assert recommendation.suggested_price_eur <= POLICY.maximum_price_eur
    assert all(abs(item.variation_pct) <= 0.1 for item in recommendation.candidates)


def test_mid_demand_keeps_the_current_price() -> None:
    recommendation = recommend_price(
        current_price_eur=12.0,
        occupancy_probability=0.50,
        scenario_name="medium",
        policy=POLICY,
    )

    assert recommendation.suggested_price_eur == 12.0
    assert recommendation.variation_pct == 0.0
    assert len(recommendation.candidates) == 5
    assert sum(item.is_allowed for item in recommendation.candidates) == 1
