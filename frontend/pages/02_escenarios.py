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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports" / "generated" / "pricing_scenarios.json"
PRICING_CONFIG_PATH = PROJECT_ROOT / "config" / "pricing_scenarios.json"
SCENARIO_LABELS = {
    "low": "Sensibilidad baja",
    "medium": "Sensibilidad media",
    "high": "Sensibilidad alta",
}
SCENARIO_DESCRIPTIONS = {
    "low": "La demanda apenas reacciona a cambios de tarifa.",
    "medium": "La demanda reacciona de forma moderada a la tarifa.",
    "high": "La demanda reacciona con fuerza a cambios de tarifa.",
}


def scenario_figure(data: pd.DataFrame) -> go.Figure:
    """Muestra el impacto neto para que las diferencias no queden ocultas."""
    labels = [SCENARIO_LABELS.get(value, value) for value in data["scenario"]]
    differences = data["expected_revenue_difference_eur"]
    colors = ["#108865" if value > 0 else "#b9c8e0" for value in differences]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Diferencia frente a tarifa fija",
            x=labels,
            y=differences,
            marker_color=colors,
            text=[f"{value:+,.0f} €".replace(",", ".") for value in differences],
            textposition="outside",
            hovertemplate="%{x}<br>Diferencia: %{y:.2f} €<extra></extra>",
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


def load_elasticities() -> dict[str, float]:
    payload = json.loads(PRICING_CONFIG_PATH.read_text(encoding="utf-8"))
    return {name: float(values["elasticity"]) for name, values in payload["scenarios"].items()}


def discount_response_pct(elasticity: float) -> float:
    """Cambio relativo de ocupación para un descuento ilustrativo del 10 %."""
    return ((0.90**-elasticity) - 1) * 100


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
    best = data.loc[data["expected_revenue_difference_eur"].idxmax()]
    baseline_revenue = float(best["expected_revenue_fixed_eur"])
    best_difference = float(best["expected_revenue_difference_eur"])
    best_changes = int(best["prices_changed"])

    first, second, third, fourth = st.columns(4)
    with first:
        metric_card("INGRESO FIJO DE REFERENCIA", format_eur(baseline_revenue), "Periodo de test")
    with second:
        metric_card(
            "MEJOR ESCENARIO",
            SCENARIO_LABELS.get(str(best["scenario"]), str(best["scenario"])),
            "Según ingreso esperado",
        )
    with third:
        metric_card("DIFERENCIA ESPERADA", format_eur(best_difference), "Frente a tarifa fija")
    with fourth:
        metric_card("TARIFAS MODIFICADAS", f"{best_changes:,}", "Turnos del periodo de test")

    st.write("")
    left, right = st.columns([1.75, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Impacto neto frente a tarifa fija")
            st.caption(
                "Así se ve la diferencia real; comparar ingresos totales ocultaba los cambios pequeños."
            )
            st.plotly_chart(scenario_figure(data), use_container_width=True)

    with right:
        with st.container(border=True):
            st.subheader("Explora una hipótesis")
            st.caption(
                "No es una estrategia comercial distinta: cambia el supuesto de respuesta al precio."
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
            selected_changes = int(value_for(data, selected, "prices_changed"))
            elasticity = load_elasticities()[selected]
            response = discount_response_pct(elasticity)
            st.markdown(f"**{SCENARIO_DESCRIPTIONS[selected]}**")
            st.metric(
                "Ingreso dinámico esperado",
                format_eur(selected_revenue),
                format_eur(selected_delta),
            )
            st.metric("Ocupación esperada", f"{selected_occupancy:,.0f} reservas", "en el periodo")
            st.metric("Cambios de tarifa", f"{selected_changes:,}")
            st.caption(
                f"Con un descuento ilustrativo del 10 %, la ocupación simulada variaría {response:+.1f} %."
            )
            if st.button("Probar en Predicciones", type="primary", use_container_width=True):
                reference_date = date.today() + timedelta(days=2)
                st.session_state.update(
                    {
                        "prediction_preferred_scenario": selected,
                        "prediction_scenario": selected,
                        "prediction_date": reference_date,
                        "prediction_court": "exterior_1",
                        "prediction_start_time": "08:00",
                        "prediction_current_price": 14.0,
                        "prediction_temperature": 22.0,
                        "prediction_precipitation": 0.0,
                        "prediction_wind": 15.0,
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
        '<div class="soft-note">ⓘ La elasticidad al precio es un supuesto configurado. '
        "Esta comparación sirve para apoyar la decisión del gestor, no para demostrar causalidad.</div>",
        unsafe_allow_html=True,
    )
