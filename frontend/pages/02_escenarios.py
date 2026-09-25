import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports" / "generated" / "pricing_scenarios.json"

st.title("Escenarios de precio")
st.caption("Comparación agregada de tarifa fija frente a regla dinámica simulada")

if not REPORT_PATH.exists():
    st.info("Ejecuta scripts/simulate_pricing_scenarios.py para generar esta comparación.")
else:
    data = pd.DataFrame(json.loads(REPORT_PATH.read_text(encoding="utf-8")))
    st.dataframe(data, use_container_width=True, hide_index=True)
    figure = px.bar(
        data,
        x="scenario",
        y="expected_revenue_difference_eur",
        color="scenario",
        title="Diferencia de ingreso esperado frente a tarifa fija",
        labels={"scenario": "Escenario", "expected_revenue_difference_eur": "Diferencia (€)"},
    )
    st.plotly_chart(figure, use_container_width=True)
    st.warning("Resultados simulados: no representan ingresos observados de un club real.")
