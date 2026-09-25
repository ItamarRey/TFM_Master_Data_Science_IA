from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import create_prediction


COURTS = ["exterior_1", "exterior_2", "exterior_3", "exterior_4", "interior_1", "interior_2"]
SLOTS = [
    "08:00",
    "09:30",
    "11:00",
    "12:30",
    "14:00",
    "15:30",
    "17:00",
    "18:30",
    "20:00",
    "21:30",
]
SCENARIOS = {
    "low": "Sensibilidad baja",
    "medium": "Sensibilidad media",
    "high": "Sensibilidad alta",
}


st.title("Predicción de un turno")
st.caption("Datos sintéticos · Predicción a 48 h · La decisión final corresponde al gestor")

with st.form("prediction_form"):
    left, right = st.columns(2)
    with left:
        selected_date = st.date_input("Fecha", value=date.today() + timedelta(days=2))
        court_id = st.selectbox("Pista", COURTS)
        start_time = st.selectbox("Hora de inicio", SLOTS, index=7)
        current_price = st.number_input(
            "Tarifa actual (€)", min_value=8.0, max_value=20.0, value=14.0, step=0.5
        )
    with right:
        scenario = st.selectbox(
            "Escenario de sensibilidad", options=list(SCENARIOS), format_func=SCENARIOS.get
        )
        st.markdown("**Pronóstico disponible 48 h antes**")
        temperature = st.slider("Temperatura prevista (°C)", 10.0, 35.0, 22.0, 0.5)
        precipitation = st.slider("Precipitación prevista (mm)", 0.0, 10.0, 0.0, 0.1)
        wind = st.slider("Viento previsto (km/h)", 0.0, 50.0, 15.0, 1.0)
    submitted = st.form_submit_button("Calcular recomendación", type="primary")

if submitted:
    payload = {
        "date": selected_date.isoformat(),
        "court_id": court_id,
        "start_time": start_time,
        "current_price": current_price,
        "scenario": scenario,
        "forecast_temperature_c": temperature,
        "forecast_precipitation_mm": precipitation,
        "forecast_wind_kmh": wind,
    }
    try:
        st.session_state["prediction_result"] = create_prediction(payload)
    except Exception as exc:
        st.error(f"No se pudo obtener la predicción: {exc}")

result = st.session_state.get("prediction_result")
if result:
    st.divider()
    st.warning(str(result["warning"]))
    first, second, third = st.columns(3)
    first.metric("Probabilidad de ocupación", f"{float(result['occupancy_probability']):.1%}")
    second.metric(
        "Tarifa sugerida",
        f"{float(result['suggested_price']):.2f} €",
        f"{float(result['variation_pct']):+.1%}",
    )
    revenue_difference = float(result["expected_revenue_suggested"]) - float(
        result["expected_revenue_current"]
    )
    third.metric(
        "Ingreso esperado por turno",
        f"{float(result['expected_revenue_suggested']):.2f} €",
        f"{revenue_difference:+.2f} €",
    )

    candidates = result["candidates"]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=[item["price_eur"] for item in candidates],
            y=[item["simulated_expected_revenue_eur"] for item in candidates],
            marker_color="#16a085",
            name="Ingreso esperado",
        )
    )
    figure.update_layout(
        title="Comparación de tarifas candidatas",
        xaxis_title="Tarifa (€)",
        yaxis_title="Ingreso esperado por turno (€)",
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("Explicación controlada")
    for item in result["explanation"]:
        st.write(f"- {item}")
    st.caption(
        f"Escenario aplicado: {result['scenario_label']}. La ocupación esperada con la tarifa "
        f"sugerida es {float(result['simulated_occupancy_probability']):.1%}."
    )
    if st.button("Simular aplicación de tarifa"):
        st.success("Acción simulada: no se ha modificado ninguna reserva ni tarifa real.")
