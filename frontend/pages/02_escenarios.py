import json
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
    labels = [SCENARIO_LABELS.get(value, value) for value in data["scenario"]]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Tarifa fija",
            x=labels,
            y=data["expected_revenue_fixed_eur"],
            marker_color="#b9c8e0",
            hovertemplate="%{x}<br>Tarifa fija: %{y:.2f} €<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            name="Regla dinámica",
            x=labels,
            y=data["expected_revenue_dynamic_eur"],
            marker_color="#2e6ae6",
            hovertemplate="%{x}<br>Regla dinámica: %{y:.2f} €<extra></extra>",
        )
    )
    figure.update_layout(
        barmode="group",
        height=360,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend={"orientation": "h", "y": 1.12},
        yaxis={"title": "Ingreso esperado (€)", "gridcolor": "#e7edf6"},
        xaxis={"title": "Escenario de sensibilidad"},
    )
    return figure


def value_for(data: pd.DataFrame, scenario: str, column: str) -> float:
    return float(data.loc[data["scenario"] == scenario, column].iloc[0])


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
            st.subheader("Impacto estimado por escenario")
            st.caption("Los importes son esperados: no son ingresos observados de un club real.")
            st.plotly_chart(scenario_figure(data), use_container_width=True)

    with right:
        with st.container(border=True):
            st.subheader("Selecciona una estrategia")
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
            st.markdown(f"**{SCENARIO_DESCRIPTIONS[selected]}**")
            st.metric(
                "Ingreso dinámico esperado",
                format_eur(selected_revenue),
                format_eur(selected_delta),
            )
            st.metric("Ocupación esperada", f"{selected_occupancy:,.0f} reservas", "en el periodo")
            st.metric("Cambios de tarifa", f"{selected_changes:,}")
            if st.button("Usar en Predicciones", type="primary", use_container_width=True):
                st.session_state["prediction_preferred_scenario"] = selected
                st.success("Escenario seleccionado. Puedes volver a Predicciones para usarlo.")
            st.page_link(
                "pages/01_predicciones.py",
                label="Ir a Predicciones",
                icon="🎯",
                use_container_width=True,
            )

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
