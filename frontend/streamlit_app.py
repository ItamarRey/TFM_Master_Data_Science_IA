import streamlit as st

st.set_page_config(page_title="PádelPulse", page_icon="🎾", layout="wide")

st.title("PádelPulse")
st.caption("MVP de predicción de ocupación y recomendación de tarifas")

st.info(
    "El proyecto trabajará con datos operativos sintéticos y meteorología pública. "
    "Las recomendaciones serán escenarios simulados, no resultados de un club real."
)

st.write("Usa el menú lateral para acceder a Predicciones, Escenarios e Histórico.")
