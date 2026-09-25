import streamlit as st

from frontend.services.api_client import get_api_health

st.set_page_config(page_title="PádelPulse", page_icon="🎾", layout="wide")

st.title("PádelPulse")
st.caption("MVP de predicción de ocupación y recomendación de tarifas")

st.info(
    "El proyecto trabajará con datos operativos sintéticos y meteorología pública. "
    "Las recomendaciones serán escenarios simulados, no resultados de un club real."
)

try:
    health = get_api_health()
    st.success(f"API disponible · estado: {health['status']}")
except Exception:
    st.warning("La API no está disponible. Iníciala con uvicorn antes de consultar predicciones.")

st.write("Usa el menú lateral para acceder a Predicciones, Escenarios e Histórico.")
