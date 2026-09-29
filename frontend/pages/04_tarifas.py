"""Calendario de tarifas activas dentro de la simulación de PádelPulse."""

from datetime import date

import pandas as pd
import streamlit as st
from components.dashboard_ui import (
    format_eur,
    inject_dashboard_styles,
    metric_card,
    render_page_header,
    render_sidebar,
)
from services.api_client import get_simulated_tariffs

st.set_page_config(page_title="PádelPulse", page_icon="🎾", layout="wide")

COURT_NAMES = {
    "exterior_1": "Exterior 1",
    "exterior_2": "Exterior 2",
    "exterior_3": "Exterior 3",
    "exterior_4": "Exterior 4",
    "interior_1": "Interior 1",
    "interior_2": "Interior 2",
}


def turn_label(tariff: dict[str, object]) -> str:
    court = COURT_NAMES.get(str(tariff["court_id"]), str(tariff["court_id"]))
    return f"{tariff['date']} · {court} · {str(tariff['start_time'])[:5]}"


inject_dashboard_styles()
render_sidebar("Tarifas")
render_page_header(
    "Tarifas programadas",
    "Revisa las tarifas activas en el calendario simulado antes de tomar nuevas decisiones.",
)

try:
    tariffs = get_simulated_tariffs()
except Exception:
    tariffs = []
    st.caption("Inicia la API para consultar las tarifas simuladas programadas.")

if not tariffs:
    st.markdown(
        '<div class="empty-state"><h3>Aún no hay tarifas programadas</h3>'
        "<p>Cuando apliques o mantengas una tarifa desde Predicciones, quedará guardada aquí. "
        "No se modifica ningún sistema real de reservas.</p></div>",
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/01_predicciones.py",
        label="Ir a Predicciones",
        icon="🎯",
        use_container_width=True,
    )
else:
    data = pd.DataFrame(tariffs)
    prices = data["price_eur"].astype(float)
    latest_update = pd.to_datetime(data["updated_at"], utc=True).max()

    first, second, third = st.columns(3)
    with first:
        metric_card("TURNOS PROGRAMADOS", str(len(data)), "Tarifas activas en simulación")
    with second:
        metric_card(
            "TARIFA MEDIA", format_eur(float(prices.mean())), "Sobre los turnos programados"
        )
    with third:
        metric_card("ÚLTIMA ACTUALIZACIÓN", latest_update.strftime("%d/%m · %H:%M"), "Hora UTC")

    st.write("")
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Calendario de tarifas activas")
            st.caption(
                "Cada fila representa la última decisión tomada para una fecha, pista y turno."
            )
            table = data.copy()
            table["Pista"] = table["court_id"].map(COURT_NAMES).fillna(table["court_id"])
            table["Hora"] = table["start_time"].astype(str).str.slice(0, 5)
            table["Tarifa"] = table["price_eur"].astype(float).map(format_eur)
            table["Actualizada"] = pd.to_datetime(table["updated_at"], utc=True).dt.strftime(
                "%d/%m/%Y · %H:%M UTC"
            )
            st.dataframe(
                table.rename(
                    columns={
                        "date": "Fecha",
                        "action_label": "Última decisión",
                    }
                )[["Fecha", "Pista", "Hora", "Tarifa", "Última decisión", "Actualizada"]],
                use_container_width=True,
                hide_index=True,
            )

    with right:
        with st.container(border=True):
            st.subheader("Revisar un turno")
            st.caption("Carga una tarifa programada en Predicciones para volver a analizarla.")
            selected_index = st.selectbox(
                "Turno programado",
                options=list(range(len(tariffs))),
                format_func=lambda index: turn_label(tariffs[index]),
            )
            selected = tariffs[selected_index]
            st.metric("Tarifa activa simulada", format_eur(float(selected["price_eur"])))
            st.caption(str(selected["action_label"]))
            if st.button("Abrir en Predicciones", type="primary", use_container_width=True):
                st.session_state.update(
                    {
                        "prediction_date": date.fromisoformat(str(selected["date"])),
                        "prediction_court": str(selected["court_id"]),
                        "prediction_start_time": str(selected["start_time"])[:5],
                        "prediction_current_price": float(selected["price_eur"]),
                        "prediction_scenario": str(selected["scenario"]),
                        "prediction_manual_weather": False,
                        "prediction_autorun": True,
                    }
                )
                st.switch_page("pages/01_predicciones.py")

    st.markdown(
        '<div class="soft-note">ⓘ Estas tarifas se guardan solo dentro de PádelPulse para hacer '
        "visible el flujo de decisión del MVP. No modifican precios, reservas ni pagos de un club real.</div>",
        unsafe_allow_html=True,
    )
