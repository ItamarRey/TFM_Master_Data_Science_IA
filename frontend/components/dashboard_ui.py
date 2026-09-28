"""Componentes visuales compartidos del dashboard de PádelPulse."""

import streamlit as st

PAGE_PATHS = {
    "Predicciones": "pages/01_predicciones.py",
    "Escenarios": "pages/02_escenarios.py",
    "Histórico": "pages/03_historico.py",
}
PAGE_ICONS = {"Predicciones": "🎯", "Escenarios": "💶", "Histórico": "📊"}


def format_eur(value: float) -> str:
    """Da formato español a una cantidad monetaria."""
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def inject_dashboard_styles() -> None:
    """Aplica una capa visual coherente en las páginas de análisis."""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #f5f7fb; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { background: #101c36; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] * { color: #eef4ff; }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
          background: transparent !important; border: 0 !important; color: #d7e2f7 !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
          background: #294575 !important; color: #ffffff !important;
        }
        .block-container { max-width: 1500px; padding-top: 2.5rem; padding-bottom: 2rem; }
        h1, h2, h3 { color: #17233f !important; }
        .page-subtitle { color: #6e7f9f; font-size: 1.05rem; margin-top: -.55rem; }
        .status-badge { display: inline-block; background: #eee7ff; color: #6736c5;
          padding: .45rem .9rem; border-radius: 999px; font-weight: 700; }
        .metric-card { background: #ffffff; border: 1px solid #dfe7f3; border-radius: .85rem;
          padding: 1.1rem 1.2rem; min-height: 118px; }
        .metric-card .label { color: #647694; font-size: .8rem; font-weight: 800; letter-spacing: .04em; }
        .metric-card .value { color: #17233f; font-size: 1.75rem; font-weight: 800; margin-top: .3rem; }
        .metric-card .detail { color: #71829d; margin-top: .25rem; }
        .soft-note { background: #e8f1ff; border-radius: .7rem; padding: .85rem 1rem; color: #315879; }
        .insight-card { background: #f0f4fb; border-radius: .65rem; padding: .9rem; min-height: 105px; }
        .insight-card strong { color: #4e6388; font-size: .78rem; letter-spacing: .04em; }
        .brand { font-size: 1.75rem; font-weight: 800; margin-top: .8rem; }
        .brand-subtitle { color: #8da0c2 !important; margin-top: -.4rem; }
        .empty-state { background: #ffffff; border: 1px dashed #b7c8e4; border-radius: .85rem;
          padding: 2rem; text-align: center; color: #516581; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(active_page: str) -> None:
    """Muestra la navegación persistente del producto."""
    with st.sidebar:
        st.markdown('<div class="brand">🎾 PádelPulse</div>', unsafe_allow_html=True)
        st.markdown('<p class="brand-subtitle">Revenue management</p>', unsafe_allow_html=True)
        st.divider()
        for label, path in PAGE_PATHS.items():
            icon = "✅" if label == active_page else PAGE_ICONS[label]
            st.page_link(path, label=label, icon=icon)
        st.divider()
        st.caption("Gestión del club\n\nModo simulación")


def render_page_header(
    title: str, subtitle: str, badge: str = "Datos sintéticos · Simulación"
) -> None:
    """Muestra el encabezado común de cada vista."""
    left, right = st.columns([4, 1.3])
    with left:
        st.title(title)
        st.markdown(f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True)
    with right:
        st.markdown(
            f'<div style="padding-top:1.2rem;text-align:right"><span class="status-badge">● {badge}</span></div>',
            unsafe_allow_html=True,
        )


def metric_card(label: str, value: str, detail: str = "") -> None:
    """Renderiza una métrica de negocio compacta."""
    st.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )
