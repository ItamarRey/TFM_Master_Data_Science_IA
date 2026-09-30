import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components.dashboard_ui import (
    format_eur,
    inject_dashboard_styles,
    metric_card,
    render_page_header,
    render_sidebar,
)

st.set_page_config(page_title="PádelPulse", page_icon="🎾", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports" / "generated" / "pricing_scenarios.json"
PRICING_CONFIG_PATH = PROJECT_ROOT / "config" / "pricing_scenarios.json"
SCENARIO_LABELS = {
    "low": "Sensibilidad baja",
    "medium": "Sensibilidad media",
    "high": "Sensibilidad alta",
}
SCENARIO_DESCRIPTIONS = {
    "low": "Hipótesis conservadora: la demanda reacciona poco a los cambios de tarifa.",
    "medium": "Hipótesis de referencia: la demanda reacciona de forma moderada a la tarifa.",
    "high": "Hipótesis exigente: la demanda reacciona con fuerza a los cambios de tarifa.",
}


def scenario_figure(data: pd.DataFrame) -> go.Figure:
    """Muestra impacto absoluto y relativo sin presentar una hipótesis como recomendación."""
    labels = [SCENARIO_LABELS.get(value, value) for value in data["scenario"]]
    differences = data["expected_revenue_difference_eur"]
    relative_differences = differences / data["expected_revenue_fixed_eur"] * 100
    colors = ["#108865" if value > 0 else "#b9c8e0" for value in differences]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Diferencia frente a tarifa fija",
            x=labels,
            y=differences,
            marker_color=colors,
            text=[
                f"{value:+,.0f} €<br>({relative:+.1f}%)".replace(",", ".")
                for value, relative in zip(differences, relative_differences, strict=True)
            ],
            textposition="outside",
            customdata=relative_differences,
            hovertemplate=(
                "%{x}<br>Diferencia: %{y:.2f} €<br>Mejora relativa: %{customdata:.2f}%<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=360,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        yaxis={"title": "Diferencia de ingreso esperado (€)", "gridcolor": "#e7edf6"},
        xaxis={"title": "Hipótesis de sensibilidad"},
        shapes=[
            {
                "type": "line",
                "x0": -0.5,
                "x1": len(labels) - 0.5,
                "y0": 0,
                "y1": 0,
                "line": {"color": "#71829d", "width": 1},
            }
        ],
    )
    return figure


def value_for(data: pd.DataFrame, scenario: str, column: str) -> float:
    return float(data.loc[data["scenario"] == scenario, column].iloc[0])


def percentage_change(value: float, baseline: float) -> float:
    """Da escala al impacto sin confundir ingreso esperado con beneficio real."""
    return value / baseline * 100 if baseline else 0.0


def load_elasticities() -> dict[str, float]:
    payload = json.loads(PRICING_CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        name: float(values["low_demand_elasticity"])
        for name, values in payload["scenarios"].items()
    }


def discount_response_pct(elasticity: float) -> float:
    """Cambio relativo de ocupación para un descuento ilustrativo del 10 %."""
    return ((0.90**-elasticity) - 1) * 100


def next_prediction_date() -> date:
    """Propone un turno cercano con previsión automática disponible."""
    return date.today() + timedelta(days=1)


inject_dashboard_styles()
render_sidebar("Escenarios")
render_page_header(
    "Escenarios de precio",
    "Compara una tarifa fija con la regla dinámica antes de decidir cómo operar el club.",
)

if not REPORT_PATH.exists():
    st.markdown(
        '<div class="empty-state"><h3>Aún no hay escenarios calculados</h3>'
        "<p>Genera el análisis de precios para comparar las alternativas de gestión.</p>"
        "<code>python scripts/simulate_pricing_scenarios.py</code></div>",
        unsafe_allow_html=True,
    )
else:
    data = pd.DataFrame(json.loads(REPORT_PATH.read_text(encoding="utf-8")))
    maximum_impact = data.loc[data["expected_revenue_difference_eur"].idxmax()]
    maximum_scenario_label = SCENARIO_LABELS.get(
        str(maximum_impact["scenario"]), str(maximum_impact["scenario"])
    )
    reference = data.loc[data["scenario"] == "medium"].iloc[0]
    baseline_revenue = float(reference["expected_revenue_fixed_eur"])
    maximum_difference = float(maximum_impact["expected_revenue_difference_eur"])
    relative_improvements = (
        data["expected_revenue_difference_eur"] / data["expected_revenue_fixed_eur"] * 100
    )
    lower_improvement = float(relative_improvements.min())
    upper_improvement = float(relative_improvements.max())

    first, second, third, fourth = st.columns(4)
    with first:
        metric_card("INGRESO FIJO DE REFERENCIA", format_eur(baseline_revenue), "Periodo de test")
    with second:
        metric_card(
            "CASO DE REFERENCIA",
            SCENARIO_LABELS["medium"],
            "Hipótesis central del MVP",
        )
    with third:
        metric_card(
            "RANGO DE MEJORA ANUAL",
            f"+{lower_improvement:.1f}% a +{upper_improvement:.1f}%",
            "Ingreso bruto esperado",
        )
    with fourth:
        metric_card(
            "MAYOR IMPACTO SIMULADO",
            format_eur(maximum_difference),
            f"≈ {format_eur(maximum_difference / 12)} al mes · {maximum_scenario_label}",
        )

    st.write("")
    left, right = st.columns([1.75, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Impacto simulado frente a tarifa fija")
            st.caption(
                "Cada barra muestra ingreso adicional esperado y su porcentaje sobre la tarifa fija."
            )
            st.plotly_chart(scenario_figure(data), use_container_width=True)

    with right:
        with st.container(border=True):
            st.subheader("Explora una hipótesis")
            st.caption(
                "No son estrategias comerciales distintas: cambian la respuesta al precio que se asume."
            )
            default_scenario = st.session_state.get("prediction_preferred_scenario", "medium")
            selected = st.selectbox(
                "Escenario para revisar",
                options=list(SCENARIO_LABELS),
                index=list(SCENARIO_LABELS).index(default_scenario),
                format_func=SCENARIO_LABELS.get,
            )
            selected_revenue = value_for(data, selected, "expected_revenue_dynamic_eur")
            selected_delta = value_for(data, selected, "expected_revenue_difference_eur")
            selected_occupancy = value_for(data, selected, "expected_occupancy_dynamic")
            fixed_occupancy = value_for(data, selected, "expected_occupancy_fixed")
            selected_fixed_revenue = value_for(data, selected, "expected_revenue_fixed_eur")
            selected_changes = int(value_for(data, selected, "prices_changed"))
            elasticity = load_elasticities()[selected]
            response = discount_response_pct(elasticity)
            relative_delta = percentage_change(selected_delta, selected_fixed_revenue)
            extra_reservations = selected_occupancy - fixed_occupancy
            relative_reservations = percentage_change(extra_reservations, fixed_occupancy)
            st.markdown(f"**{SCENARIO_DESCRIPTIONS[selected]}**")
            st.metric(
                "Ingreso anual esperado",
                format_eur(selected_revenue),
                f"{format_eur(selected_delta)} · {relative_delta:+.2f}%",
            )
            st.metric(
                "Equivalente mensual",
                format_eur(selected_delta / 12),
                "Ingreso bruto esperado adicional",
            )
            st.metric(
                "Reservas adicionales esperadas",
                f"+{extra_reservations:,.0f}",
                f"{relative_reservations:+.1f}% frente a tarifa fija",
            )
            st.metric("Cambios de tarifa", f"{selected_changes:,}")
            st.caption(
                f"Con un descuento ilustrativo del 10 %, la ocupación simulada variaría {response:+.1f} %."
            )
            if st.button("Probar en Predicciones", type="primary", use_container_width=True):
                peak_scenario = selected in {"low", "medium"}
                st.session_state.update(
                    {
                        "prediction_preferred_scenario": selected,
                        "prediction_scenario": selected,
                        "prediction_date": next_prediction_date(),
                        "prediction_court": "exterior_1",
                        "prediction_start_time": "20:00" if peak_scenario else "08:00",
                        "prediction_current_price": 21.0 if peak_scenario else 16.0,
                        "prediction_manual_weather": False,
                        "prediction_autorun": True,
                    }
                )
                st.switch_page("pages/01_predicciones.py")

    with st.container(border=True):
        st.subheader("Detalle de la simulación")
        table = data.copy()
        table["scenario"] = table["scenario"].map(SCENARIO_LABELS)
        table = table.rename(
            columns={
                "scenario": "Escenario",
                "prices_changed": "Tarifas modificadas",
                "expected_occupancy_fixed": "Reservas fijas esperadas",
                "expected_occupancy_dynamic": "Reservas dinámicas esperadas",
                "expected_revenue_fixed_eur": "Ingreso fijo esperado (€)",
                "expected_revenue_dynamic_eur": "Ingreso dinámico esperado (€)",
                "expected_revenue_difference_eur": "Diferencia (€)",
            }
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="soft-note">ⓘ La sensibilidad media es el caso de referencia. El rango '
        "mostrado equivale aproximadamente a una mejora anual del ingreso bruto esperado, no a "
        "beneficio garantizado. La elasticidad al precio es un supuesto configurado; esta "
        "comparación no demuestra causalidad en un club real.</div>",
        unsafe_allow_html=True,
    )
