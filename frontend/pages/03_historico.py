import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from components.dashboard_ui import (
    format_eur,
    inject_dashboard_styles,
    metric_card,
    render_page_header,
    render_sidebar,
)
from services.api_client import get_decisions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDA_PATH = PROJECT_ROOT / "reports" / "generated" / "eda_metrics.json"


def occupancy_chart(data: pd.DataFrame, x: str, title: str, labels: dict[str, str]) -> object:
    figure = px.bar(
        data,
        x=x,
        y="ocupacion_pct",
        color="ocupacion_pct",
        color_continuous_scale=["#dce9ff", "#2e6ae6"],
        text="ocupacion_pct",
        title=title,
        labels={**labels, "ocupacion_pct": "Ocupación (%)"},
    )
    figure.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    figure.update_layout(
        height=330,
        margin={"l": 10, "r": 10, "t": 55, "b": 10},
        paper_bgcolor="white",
        plot_bgcolor="white",
        coloraxis_showscale=False,
        yaxis={"range": [0, 100], "gridcolor": "#e7edf6"},
    )
    return figure


def find_peak(data: pd.DataFrame, label_column: str) -> tuple[str, float]:
    top = data.loc[data["ocupacion_pct"].idxmax()]
    return str(top[label_column]), float(top["ocupacion_pct"])


inject_dashboard_styles()
render_sidebar("Histórico")
render_page_header(
    "Histórico de ocupación",
    "Detecta patrones de demanda en el escenario simulado antes de revisar una tarifa.",
)

if not EDA_PATH.exists():
    st.markdown(
        '<div class="empty-state"><h3>Aún no hay indicadores históricos</h3>'
        "<p>Genera el análisis exploratorio para alimentar esta vista.</p>"
        "<code>python scripts/run_eda.py</code></div>",
        unsafe_allow_html=True,
    )
else:
    analysis = json.loads(EDA_PATH.read_text(encoding="utf-8"))
    summary = analysis["summary"]
    time_band = pd.DataFrame(analysis["occupancy_by_time_band"])
    day = pd.DataFrame(analysis["occupancy_by_day"])
    court_type = pd.DataFrame(analysis["occupancy_by_court_type"])
    weather = pd.DataFrame(analysis["exterior_weather_impact"])
    peak_band, peak_band_occupancy = find_peak(time_band, "franja_horaria")
    peak_day, peak_day_occupancy = find_peak(day, "dia_semana_es")

    first, second, third, fourth = st.columns(4)
    with first:
        metric_card("TURNOS OFERTADOS", f"{int(summary['turnos_totales']):,}", "Escenario completo")
    with second:
        metric_card(
            "OCUPACIÓN ELEGIBLE",
            f"{float(summary['ocupacion_final_pct']):.1f}%",
            "Turnos no bloqueados",
        )
    with third:
        metric_card(
            "INGRESOS SIMULADOS",
            format_eur(float(summary["ingresos_finales_eur"])),
            "Resultado operativo",
        )
    with fourth:
        metric_card(
            "CANCELACIONES",
            f"{float(summary['cancelaciones_pct']):.1f}%",
            "Sobre turnos no bloqueados",
        )

    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.plotly_chart(
                occupancy_chart(
                    time_band,
                    "franja_horaria",
                    "Ocupación por franja horaria",
                    {"franja_horaria": "Franja"},
                ),
                use_container_width=True,
            )
    with right:
        with st.container(border=True):
            st.plotly_chart(
                occupancy_chart(
                    day,
                    "dia_semana_es",
                    "Ocupación por día de la semana",
                    {"dia_semana_es": "Día"},
                ),
                use_container_width=True,
            )

    first, second = st.columns(2, gap="large")
    with first:
        with st.container(border=True):
            st.plotly_chart(
                occupancy_chart(
                    weather,
                    "categoria_lluvia",
                    "Efecto de la lluvia en pistas exteriores",
                    {"categoria_lluvia": "Precipitación"},
                ),
                use_container_width=True,
            )
    with second:
        with st.container(border=True):
            st.plotly_chart(
                occupancy_chart(
                    court_type,
                    "tipo_pista",
                    "Ocupación por tipo de pista",
                    {"tipo_pista": "Tipo de pista"},
                ),
                use_container_width=True,
            )

    st.subheader("Lecturas rápidas para el gestor")
    insights = st.columns(3)
    insights[0].markdown(
        f'<div class="insight-card"><strong>FRANJA CON MÁS DEMANDA</strong><br><br>'
        f"<b>{peak_band.title()}</b><br>{peak_band_occupancy:.1f}% de ocupación simulada</div>",
        unsafe_allow_html=True,
    )
    insights[1].markdown(
        f'<div class="insight-card"><strong>DÍA CON MÁS DEMANDA</strong><br><br>'
        f"<b>{peak_day}</b><br>{peak_day_occupancy:.1f}% de ocupación simulada</div>",
        unsafe_allow_html=True,
    )
    rain_free = weather.loc[weather["categoria_lluvia"] == "Sin lluvia", "ocupacion_pct"]
    rain_high = weather.loc[
        weather["categoria_lluvia"] == "Lluvia moderada o alta", "ocupacion_pct"
    ]
    if not rain_free.empty and not rain_high.empty:
        rain_difference = float(rain_free.iloc[0] - rain_high.iloc[0])
        rain_text = f"{rain_difference:.1f} puntos menos con lluvia intensa"
    else:
        rain_text = "Sin comparación disponible"
    insights[2].markdown(
        f'<div class="insight-card"><strong>IMPACTO METEOROLÓGICO</strong><br><br>{rain_text}'
        "<br>Solo en pistas exteriores</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Decisiones recientes del gestor")
    try:
        decisions = get_decisions()
    except Exception:
        decisions = []
        st.caption("Inicia la API para consultar las decisiones simuladas registradas.")
    if decisions:
        decision_data = pd.DataFrame(decisions)
        decision_data["created_at"] = pd.to_datetime(
            decision_data["created_at"], utc=True
        ).dt.strftime("%d/%m/%Y %H:%M")
        decision_data["turno"] = (
            decision_data["date"].astype(str)
            + " · "
            + decision_data["court_id"].str.replace("_", " ").str.title()
            + " · "
            + decision_data["start_time"].astype(str).str.slice(0, 5)
        )
        decision_data["ocupacion"] = (
            decision_data["occupancy_probability"].astype(float) * 100
        ).round(1).astype(str) + "%"
        decision_data["tarifa"] = decision_data.apply(
            lambda row: format_eur(
                float(row["suggested_price"])
                if row["action"] == "apply_suggested"
                else float(row["current_price"])
            ),
            axis=1,
        )
        st.dataframe(
            decision_data.rename(
                columns={
                    "created_at": "Registrada",
                    "action_label": "Decisión",
                    "turno": "Turno",
                    "ocupacion": "Ocupación estimada",
                    "tarifa": "Tarifa registrada",
                }
            )[["Registrada", "Decisión", "Turno", "Ocupación estimada", "Tarifa registrada"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Todavía no hay decisiones registradas. Puedes crear una desde Predicciones.")

    st.markdown(
        '<div class="soft-note">ⓘ Los patrones describen exclusivamente el escenario sintético. '
        "Sirven para entender la demanda simulada, no para afirmar el comportamiento de un club real.</div>",
        unsafe_allow_html=True,
    )
