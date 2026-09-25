import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EDA_PATH = PROJECT_ROOT / "reports" / "generated" / "eda_metrics.json"

st.title("Histórico simulado")
st.caption("Resumen exploratorio de Gold; no corresponde a la operación de un club real")

if not EDA_PATH.exists():
    st.info("Ejecuta scripts/run_eda.py para generar los indicadores históricos.")
else:
    analysis = json.loads(EDA_PATH.read_text(encoding="utf-8"))
    summary = analysis["summary"]
    first, second, third = st.columns(3)
    first.metric("Turnos ofertados", f"{summary['turnos_totales']:,}")
    second.metric("Ocupación elegible", f"{summary['ocupacion_final_pct']:.2f}%")
    third.metric("Ingresos simulados", f"{summary['ingresos_finales_eur']:,.2f} €")
    occupancy = pd.DataFrame(analysis["occupancy_by_time_band"])
    figure = px.bar(
        occupancy,
        x="franja_horaria",
        y="ocupacion_pct",
        color="franja_horaria",
        title="Ocupación simulada por franja horaria",
        labels={"franja_horaria": "Franja", "ocupacion_pct": "Ocupación (%)"},
    )
    st.plotly_chart(figure, use_container_width=True)
