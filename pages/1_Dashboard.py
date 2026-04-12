"""
Página 1: Dashboard / Home
Resumen general de la biblioteca.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import UTC, datetime

from storage.database import get_stats, init_db

st.set_page_config(page_title="Dashboard — MedLib", page_icon="📊", layout="wide")

# Garantizar BD inicializada al acceder directamente a la pagina
init_db()

st.title("📊 Dashboard")
st.caption(f"Actualizado: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

# ─── Cargar estadísticas ──────────────────────────────────────────────────────
try:
    stats = get_stats()
except Exception as e:
    st.error(f"Error cargando estadísticas: {e}")
    st.stop()

# ─── Métricas principales ─────────────────────────────────────────────────────
st.subheader("Resumen General")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Artículos", stats["total"])
c2.metric("Con PDF", stats["with_pdf"])
c3.metric("Pendientes", stats["pending"])
c4.metric("Prioritarios", stats["priority"])
c5.metric("Grupos de Duplicados", stats["flags"].get("duplicates", 0))

st.markdown("---")

# ─── Alertas de calidad ───────────────────────────────────────────────────────
flags = stats.get("flags", {})
alert_items = []
if flags.get("no_abstract", 0):
    alert_items.append(f"⚠️ **{flags['no_abstract']}** artículos sin abstract")
if flags.get("incomplete", 0):
    alert_items.append(f"⚠️ **{flags['incomplete']}** registros con metadatos incompletos")
if flags.get("preprints", 0):
    alert_items.append(f"📄 **{flags['preprints']}** preprints en la biblioteca")
if flags.get("predatory", 0):
    alert_items.append(f"🚩 **{flags['predatory']}** artículos en revistas potencialmente dudosas")

if alert_items:
    with st.expander("🔔 Alertas de Calidad", expanded=True):
        for item in alert_items:
            st.markdown(item)
else:
    st.success("✅ No hay alertas de calidad activas.")

# ─── Distribución por colección ───────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Artículos por Colección")
    by_col = stats.get("by_collection", [])
    if by_col:
        df_col = pd.DataFrame(by_col)
        df_col.columns = ["Colección", "Artículos"]
        st.dataframe(df_col, use_container_width=True, hide_index=True)
    else:
        st.info("No hay colecciones registradas.")

with col_right:
    st.subheader("Artículos por Fuente")
    by_source = stats.get("by_source", [])
    if by_source:
        df_src = pd.DataFrame(by_source)
        df_src.columns = ["Fuente", "Artículos"]
        st.dataframe(df_src, use_container_width=True, hide_index=True)
    else:
        st.info("No hay fuentes registradas.")

# ─── Últimas búsquedas ────────────────────────────────────────────────────────
st.subheader("Últimas Búsquedas")
recent = stats.get("recent_searches", [])
if recent:
    df_searches = pd.DataFrame(recent)[
        ["timestamp", "source", "query", "result_count", "saved_count", "collection_name", "error"]
    ].rename(columns={
        "timestamp": "Fecha",
        "source": "Fuente",
        "query": "Query",
        "result_count": "Resultados",
        "saved_count": "Guardados",
        "collection_name": "Colección",
        "error": "Error",
    })
    df_searches["Query"] = df_searches["Query"].str[:60] + "…"
    st.dataframe(df_searches, use_container_width=True, hide_index=True)
else:
    st.info("Todavía no hay búsquedas registradas. Ve a **Search** para comenzar.")
