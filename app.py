"""
MedLib — Biblioteca Personal de Literatura Científica Biomédica
Entry point principal de Streamlit.
"""
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from storage.database import init_db
from utils import setup_logging

# Configurar logging
Path("data").mkdir(exist_ok=True)
setup_logging("INFO")

# Inicializar DB
init_db()

st.set_page_config(
    page_title="MedLib",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS global
st.markdown("""
<style>
    /* Fuente principal */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f1923;
        border-right: 1px solid #1e3a5f;
    }
    [data-testid="stSidebar"] * {
        color: #b8d4e8 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] p {
        color: #7fa8c9 !important;
        font-size: 0.82rem;
    }

    /* Header principal */
    h1 { color: #1a6ca8; font-weight: 600; }
    h2 { color: #2980b9; font-weight: 500; }
    h3 { color: #3498db; font-weight: 500; }

    /* Métricas */
    [data-testid="metric-container"] {
        background: #f0f7ff;
        border: 1px solid #d0e8f7;
        border-radius: 8px;
        padding: 0.8rem;
    }
    [data-testid="metric-container"] label {
        color: #5a7fa0 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        color: #1a4a6e !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
    }

    /* Botones */
    .stButton > button {
        background: #1a6ca8;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background: #155a8a;
    }

    /* Tablas */
    [data-testid="stDataFrame"] {
        border: 1px solid #d0e8f7;
        border-radius: 8px;
    }

    /* Alerts */
    .stAlert { border-radius: 8px; }

    /* Badge de score */
    .score-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
    }
    .score-high { background: #d4edda; color: #155724; }
    .score-mid  { background: #fff3cd; color: #856404; }
    .score-low  { background: #f8d7da; color: #721c24; }

    /* Ficha de artículo */
    .article-card {
        background: white;
        border: 1px solid #d0e8f7;
        border-left: 4px solid #1a6ca8;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }
    .article-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1a4a6e;
        margin-bottom: 0.3rem;
    }
    .article-meta {
        font-size: 0.78rem;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar con logo y navegación
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 1.5rem;'>
        <span style='font-size: 2.5rem;'>🔬</span>
        <div style='font-size: 1.2rem; font-weight: 600; color: #4da6e0; margin-top: 0.3rem;'>
            MedLib
        </div>
        <div style='font-size: 0.72rem; color: #4a7a9b; letter-spacing: 0.08em; text-transform: uppercase;'>
            Biblioteca Biomédica
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Versión 0.1.0 · MVP")
    st.caption("PubMed · Europe PMC · Crossref · OpenAlex")

# Página de inicio
st.title("🔬 MedLib — Biblioteca Personal Biomédica")

st.markdown("""
Bienvenido a **MedLib**, tu biblioteca personal de literatura científica biomédica.

Usa el menú lateral para navegar entre las secciones:
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**🔍 Search**\nBusca en PubMed, Europe PMC, Crossref y OpenAlex")
    st.info("**📚 Library**\nVisualiza y gestiona tu biblioteca")
with col2:
    st.info("**🔀 Duplicates**\nRevisa y resuelve duplicados potenciales")
    st.info("**📤 Exports**\nExporta a CSV, JSON, RIS, BibTeX, NotebookLM")
with col3:
    st.info("**🔍 Audit**\nDetecta problemas de calidad en tus registros")
    st.info("**⚙️ Settings**\nConfigura API keys y parámetros")

st.markdown("---")
st.markdown(
    "_MedLib usa únicamente APIs oficiales públicas. "
    "No intenta eludir restricciones de acceso ni paywalls._"
)
