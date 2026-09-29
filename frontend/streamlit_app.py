"""Punto de entrada del MVP.

El flujo operativo empieza directamente en Predicciones; no hay una portada
intermedia que añada un paso sin aportar información al gestor.
"""

import streamlit as st


st.set_page_config(page_title="PádelPulse", page_icon="🎾", layout="wide")
st.switch_page("pages/01_predicciones.py")
