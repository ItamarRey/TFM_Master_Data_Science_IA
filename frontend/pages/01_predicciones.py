from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from services.api_client import create_prediction


COURTS = {
    "exterior_1": "Exterior 1",
    "exterior_2": "Exterior 2",
    "exterior_3": "Exterior 3",
    "exterior_4": "Exterior 4",
    "interior_1": "Interior 1",
    "interior_2": "Interior 2",
}
SLOTS = ["08:00", "09:30", "11:00", "12:30", "14:00", "15:30", "17:00", "18:30", "20:00", "21:30"]
SCENARIOS = {
    "low": "Sensibilidad baja",
    "medium": "Sensibilidad media",
    "high": "Sensibilidad alta",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #f5f7fb; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { background: #101c36; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] * { color: #eef4ff; }
        [data-testid="stSidebar"] .stButton > button {
          justify-content: flex-start; color: #d7e2f7; background: transparent;
          border: 0; box-shadow: none;
        }
        [data-testid="stSidebar"] .stButton > button:hover { background: #294575; }
        .block-container { max-width: 1600px; padding-top: 2.5rem; padding-bottom: 2rem; }
        h1, h2, h3 { color: #17233f !important; }
        .app-kicker { color: #6e7f9f; font-size: 1.05rem; margin-top: -0.6rem; }
        .status-badge { display: inline-block; background: #eee7ff; color: #6736c5;
          padding: .45rem .9rem; border-radius: 999px; font-weight: 700; }
        .step-label { color: #2d6de1; font-weight: 800; letter-spacing: .03em; }
        .card-caption { color: #72829f; }
        .metric-label { color: #5c6d8b; font-size: .82rem; font-weight: 800; letter-spacing: .04em; }
        .big-probability { color: #17233f; font-size: 2.45rem; font-weight: 800; line-height: 1; }
        .demand-chip { display: inline-block; margin-left: .65rem; padding: .35rem .65rem;
          border-radius: 999px; font-weight: 700; vertical-align: .3rem; }
        .chip-low { background: #fff1d8; color: #ad6800; }
        .chip-mid { background: #e5efff; color: #2460c8; }
        .chip-high { background: #ddf6ec; color: #087a55; }
        .result-stat { border-top: 1px solid #e4eaf4; padding-top: .85rem; }
        .result-stat strong { color: #17233f; font-size: 1.15rem; }
        .price-decision { background: #edf9f4; border: 1px solid #bdebd9;
          border-radius: .8rem; padding: 1.35rem; }
        .price-value { color: #108865; font-size: 2.45rem; font-weight: 800; line-height: 1.2; }
        .soft-alert { background: #fff7e7; border: 1px solid #f3d18e; border-radius: .7rem;
          padding: .8rem 1rem; color: #805800; }
        .info-footer { background: #e8f1ff; color: #315879; padding: .9rem 1.1rem;
          border-radius: .7rem; font-weight: 600; }
        .factor-card { background: #f0f4fb; padding: .8rem; border-radius: .65rem;
          min-height: 95px; }
        .factor-card strong { color: #4e6388; font-size: .8rem; letter-spacing: .04em; }
        .brand { font-size: 1.75rem; font-weight: 800; margin-top: .8rem; }
        .brand-subtitle { color: #8da0c2 !important; margin-top: -.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_eur(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def demand_label(probability: float) -> tuple[str, str]:
    if probability < 0.35:
        return "Demanda baja", "chip-low"
    if probability > 0.65:
        return "Demanda alta", "chip-high"
    return "Demanda intermedia", "chip-mid"


def show_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="brand">🎾 PádelPulse</div>', unsafe_allow_html=True)
        st.markdown('<p class="brand-subtitle">Revenue management</p>', unsafe_allow_html=True)
        st.divider()
        st.page_link("pages/01_predicciones.py", label="Predicciones", icon="🎯")
        st.page_link("pages/02_escenarios.py", label="Escenarios", icon="💶")
        st.page_link("pages/03_historico.py", label="Histórico", icon="📊")
        st.divider()
        st.caption("Gestión del club\n\nModo simulación")


def build_price_figure(candidates: list[dict[str, object]], suggested_price: float) -> go.Figure:
    ordered = sorted(candidates, key=lambda item: float(item["price_eur"]))
    prices = [float(item["price_eur"]) for item in ordered]
    occupancy = [float(item["simulated_occupancy_probability"]) * 100 for item in ordered]
    allowed = [bool(item["is_allowed"]) for item in ordered]
    marker_colors = ["#2e6ae6" if item else "#b4c1d6" for item in allowed]
    marker_symbols = ["circle" if item else "x" for item in allowed]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=prices,
            y=occupancy,
            mode="lines+markers",
            line={"color": "#2e6ae6", "width": 3},
            marker={"size": 10, "color": marker_colors, "symbol": marker_symbols},
            customdata=["Permitida" if item else "No permitida por la regla" for item in allowed],
            hovertemplate="Tarifa: %{x:.2f} €<br>Ocupación: %{y:.1f}%<br>%{customdata}<extra></extra>",
        )
    )
    selected = next(item for item in ordered if float(item["price_eur"]) == suggested_price)
    figure.add_trace(
        go.Scatter(
            x=[suggested_price],
            y=[float(selected["simulated_occupancy_probability"]) * 100],
            mode="markers",
            marker={"size": 16, "color": "#108865", "line": {"color": "white", "width": 3}},
            hovertemplate="Tarifa sugerida: %{x:.2f} €<extra></extra>",
        )
    )
    figure.update_layout(
        height=295,
        margin={"l": 15, "r": 15, "t": 15, "b": 10},
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        xaxis={"title": "Tarifa (€)", "showgrid": False},
        yaxis={"title": "Ocupación estimada", "ticksuffix": "%", "gridcolor": "#e7edf6"},
    )
    return figure


inject_styles()
show_sidebar()

header_left, header_right = st.columns([4, 1.35])
with header_left:
    st.title("Predicción de ocupación y tarifa sugerida")
    st.markdown(
        '<p class="app-kicker">Decide el precio de un turno concreto con contexto y control.</p>',
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown(
        '<div style="padding-top:1.2rem;text-align:right"><span class="status-badge">● Datos sintéticos · Simulación</span></div>',
        unsafe_allow_html=True,
    )

left, center, right = st.columns([1.1, 2.05, 1.15], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<span class="step-label">1 &nbsp; CONFIGURA LA PREDICCIÓN</span>', unsafe_allow_html=True)
        st.markdown('<p class="card-caption">Selecciona el turno a analizar</p>', unsafe_allow_html=True)
        with st.form("prediction_form"):
            selected_date = st.date_input("Fecha", value=date.today() + timedelta(days=2))
            court_id = st.selectbox("Pista", options=list(COURTS), format_func=COURTS.get)
            start_time = st.selectbox("Turno", SLOTS, index=7)
            current_price = st.number_input("Tarifa base (€)", 8.0, 20.0, 14.0, 0.5)
            st.markdown("**Previsión disponible 48 h antes**")
            temperature = st.slider("Temperatura prevista (°C)", 10.0, 35.0, 22.0, 0.5)
            precipitation = st.slider("Lluvia prevista (mm)", 0.0, 10.0, 0.0, 0.1)
            wind = st.slider("Viento previsto (km/h)", 0.0, 50.0, 15.0, 1.0)
            scenario = st.selectbox("Escenario de sensibilidad", list(SCENARIOS), format_func=SCENARIOS.get)
            submitted = st.form_submit_button("Actualizar predicción", type="primary", use_container_width=True)
        st.caption("Las variables se consideran conocidas 48 horas antes del turno.")

if submitted:
    payload = {
        "date": selected_date.isoformat(), "court_id": court_id, "start_time": start_time,
        "current_price": current_price, "scenario": scenario,
        "forecast_temperature_c": temperature, "forecast_precipitation_mm": precipitation,
        "forecast_wind_kmh": wind,
    }
    try:
        st.session_state["prediction_result"] = create_prediction(payload)
        st.session_state["prediction_inputs"] = payload
    except Exception as exc:
        st.error(f"No se pudo obtener la predicción: {exc}")

result = st.session_state.get("prediction_result")
inputs = st.session_state.get("prediction_inputs", {})

with center:
    with st.container(border=True):
        st.markdown('<span class="step-label">2 &nbsp; RESULTADO ESTIMADO</span>', unsafe_allow_html=True)
        if not result:
            st.info("Configura un turno y pulsa **Actualizar predicción** para ver el resultado.")
        else:
            probability = float(result["occupancy_probability"])
            demand, demand_class = demand_label(probability)
            st.markdown('<p class="metric-label">PROBABILIDAD DE OCUPACIÓN</p>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="big-probability">{probability:.0%}</span><span class="demand-chip {demand_class}">{demand}</span>',
                unsafe_allow_html=True,
            )
            st.divider()
            stats = st.columns(3)
            minimum = min(float(item["simulated_occupancy_probability"]) for item in result["candidates"])
            maximum = max(float(item["simulated_occupancy_probability"]) for item in result["candidates"])
            stats[0].markdown(f'<div class="result-stat"><span class="card-caption">Rango comparado</span><br><strong>{minimum:.0%} – {maximum:.0%}</strong></div>', unsafe_allow_html=True)
            stats[1].markdown('<div class="result-stat"><span class="card-caption">Calidad del dato</span><br><strong style="color:#108865">Alta</strong></div>', unsafe_allow_html=True)
            stats[2].markdown('<div class="result-stat"><span class="card-caption">Estado</span><br><strong>Listo para revisar</strong></div>', unsafe_allow_html=True)
            st.caption("Estimación de una simulación; no es un resultado observado de un club real.")

    if result:
        with st.container(border=True):
            st.subheader("Ocupación estimada por precio")
            st.caption("Compara las tarifas candidatas para este mismo turno.")
            st.plotly_chart(build_price_figure(result["candidates"], float(result["suggested_price"])), use_container_width=True)
            st.caption("Los marcadores grises se visualizan para comparar, pero no están permitidos por la regla de negocio para esta demanda.")

        with st.container(border=True):
            st.subheader("Por qué aparece esta recomendación")
            factor_columns = st.columns(3)
            weather_text = f'{float(inputs.get("forecast_temperature_c", 0)):.0f} °C · {float(inputs.get("forecast_precipitation_mm", 0)):.1f} mm'
            factor_columns[0].markdown(f'<div class="factor-card"><strong>METEOROLOGÍA</strong><br><br>{weather_text}</div>', unsafe_allow_html=True)
            factor_columns[1].markdown(f'<div class="factor-card"><strong>FRANJA HORARIA</strong><br><br>{inputs.get("start_time", "—")}</div>', unsafe_allow_html=True)
            factor_columns[2].markdown(f'<div class="factor-card"><strong>ESCENARIO DE PRECIO</strong><br><br>{result["scenario_label"]}</div>', unsafe_allow_html=True)
            for item in result["explanation"]:
                st.write(f"- {item}")

with right:
    with st.container(border=True):
        st.markdown('<span class="step-label" style="color:#108865">3 &nbsp; DECIDE LA TARIFA</span>', unsafe_allow_html=True)
        st.markdown('<p class="card-caption">Recomendación para este turno</p>', unsafe_allow_html=True)
        if not result:
            st.info("El resultado aparecerá aquí tras calcular la predicción.")
        else:
            suggested_price = float(result["suggested_price"])
            variation = float(result["variation_pct"])
            if variation == 0:
                decision_text, objective = "Mantener tarifa base", "No se recomienda cambio para esta demanda"
            elif variation < 0:
                decision_text, objective = "Reducir tarifa", "Objetivo: incentivar la ocupación"
            else:
                decision_text, objective = "Incrementar tarifa", "Objetivo: capturar demanda alta"
            st.markdown('<div class="price-decision">', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">TARIFA SUGERIDA</p>', unsafe_allow_html=True)
            st.markdown(f'<div class="price-value">{format_eur(suggested_price)}</div>', unsafe_allow_html=True)
            st.markdown(f"**{variation:+.0%}** respecto a la tarifa base · {decision_text}")
            st.write(objective)
            st.caption("Revisión requerida antes de aplicar")
            st.markdown("</div>", unsafe_allow_html=True)
            st.subheader("Acciones disponibles")
            if st.button("Aplicar tarifa sugerida", type="primary", use_container_width=True):
                st.session_state["applied_message"] = "Acción simulada: no se ha modificado ninguna reserva ni tarifa real."
            if st.button("Mantener tarifa base", use_container_width=True):
                st.session_state["applied_message"] = "Acción simulada: se mantiene la tarifa base."
            st.page_link("pages/02_escenarios.py", label="Comparar escenarios", icon="📈", use_container_width=True)
            if message := st.session_state.get("applied_message"):
                st.success(message)
            difference = float(result["expected_revenue_suggested"]) - float(result["expected_revenue_current"])
            st.markdown(f'<div class="soft-alert"><strong>Ingreso esperado del turno: {format_eur(float(result["expected_revenue_suggested"]))}</strong><br>Media simulada (probabilidad × tarifa), no ingreso garantizado. Diferencia frente a la base: {format_eur(difference)}.</div>', unsafe_allow_html=True)

st.markdown('<div class="info-footer">ⓘ La predicción usa datos operativos sintéticos y previsión meteorológica pública. Puedes revisar o rechazar la recomendación.</div>', unsafe_allow_html=True)
