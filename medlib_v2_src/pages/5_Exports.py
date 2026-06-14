"""
Página 5: Exportaciones.
CSV, JSON, RIS, BibTeX y paquete NotebookLM.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import UTC, datetime

from storage.database import get_all_articles, get_collections
from exporters.exporters import (
    to_csv_bytes, to_json_bytes, to_ris_bytes,
    to_bibtex_bytes, generate_notebooklm_zip
)

st.set_page_config(page_title="Exports — MedLib", page_icon="📤", layout="wide")

st.title("📤 Exportaciones")
st.caption("Exporta tu biblioteca en múltiples formatos.")

# ─── Filtros de exportación ───────────────────────────────────────────────────
st.subheader("1. Seleccionar subconjunto")

with st.form("export_filters"):
    col1, col2, col3 = st.columns(3)

    collections = [""] + get_collections()
    collection_filter = col1.selectbox(
        "Colección",
        collections,
        format_func=lambda x: "Todas las colecciones" if x == "" else x
    )
    status_filter = col2.selectbox(
        "Estado de lectura",
        ["", "pending", "reading", "read", "priority", "included"],
        format_func=lambda x: "Todos" if x == "" else x
    )
    min_score = col3.slider("Score mínimo", 0, 100, 0, step=5)

    submitted = st.form_submit_button("🔄 Cargar artículos", type="primary")

# Cargar artículos (inicialmente o tras aplicar filtros)
if "export_articles" not in st.session_state or submitted:
    articles = get_all_articles(
        collection=collection_filter or None,
        read_status=status_filter or None,
        min_score=min_score if min_score > 0 else None,
        limit=5000,
    )
    st.session_state["export_articles"] = articles
    st.session_state["export_collection_name"] = collection_filter or "medlib_export"

articles = st.session_state.get("export_articles", [])
collection_name = st.session_state.get("export_collection_name", "medlib_export")

if not articles:
    st.warning("No hay artículos que exportar con los filtros actuales.")
    st.stop()

st.success(f"**{len(articles)} artículos** listos para exportar.")

timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M")

# ─── Formatos estándar ────────────────────────────────────────────────────────
st.subheader("2. Formatos estándar")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### CSV")
    st.caption("Compatible con Excel, Google Sheets y cualquier gestor de datos.")
    try:
        csv_bytes = to_csv_bytes(articles)
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=f"medlib_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error: {e}")

with col2:
    st.markdown("#### JSON")
    st.caption("Metadatos completos en formato estructurado.")
    try:
        json_bytes = to_json_bytes(articles)
        st.download_button(
            "⬇️ Descargar JSON",
            data=json_bytes,
            file_name=f"medlib_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error: {e}")

with col3:
    st.markdown("#### RIS")
    st.caption("Compatible con Zotero, Mendeley, EndNote y gestores bibliográficos.")
    try:
        ris_bytes = to_ris_bytes(articles)
        st.download_button(
            "⬇️ Descargar RIS",
            data=ris_bytes,
            file_name=f"medlib_{timestamp}.ris",
            mime="application/x-research-info-systems",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error: {e}")

with col4:
    st.markdown("#### BibTeX")
    st.caption("Para LaTeX, Overleaf y sistemas de citación académica.")
    try:
        bib_bytes = to_bibtex_bytes(articles)
        st.download_button(
            "⬇️ Descargar BibTeX",
            data=bib_bytes,
            file_name=f"medlib_{timestamp}.bib",
            mime="text/plain",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")

# ─── Exportación NotebookLM ───────────────────────────────────────────────────
st.subheader("3. Paquete NotebookLM")

st.markdown("""
El paquete NotebookLM genera un archivo **ZIP** con:
- 📄 `README.md` — Descripción de la colección
- 📊 `resumen_master.csv` — Tabla completa de artículos
- 🗂️ `metadata.json` — Metadatos estructurados
- 📝 `fichas/` — Ficha individual en Markdown por artículo

**Uso:** Sube los archivos `.md` y el CSV directamente a NotebookLM como fuentes.
""")

col_nb1, col_nb2 = st.columns([2, 1])
with col_nb1:
    nb_collection_name = st.text_input(
        "Nombre de la colección para el ZIP",
        value=collection_name.replace(" ", "_") or "mi_coleccion",
    )

with col_nb2:
    st.markdown(" ")  # spacer
    st.markdown(" ")

st.info(f"Se generarán **{len(articles)} fichas** en Markdown + archivos master.")

# Advertencia si hay muchos artículos
if len(articles) > 200:
    st.warning(
        f"⚠️ {len(articles)} artículos es un número elevado. "
        "La generación del ZIP puede tardar unos segundos. "
        "Considera filtrar a un subconjunto más específico para NotebookLM."
    )

if st.button("📦 Generar paquete NotebookLM", type="primary"):
    with st.spinner("Generando paquete…"):
        try:
            zip_bytes = generate_notebooklm_zip(articles, nb_collection_name)
            st.download_button(
                "⬇️ Descargar ZIP para NotebookLM",
                data=zip_bytes,
                file_name=f"notebooklm_{nb_collection_name}_{timestamp}.zip",
                mime="application/zip",
                use_container_width=True,
            )
            st.success(
                f"✅ Paquete generado con {len(articles)} fichas. "
                "Descárgalo y sube los archivos a NotebookLM."
            )
        except Exception as e:
            st.error(f"Error generando el paquete: {e}")

st.markdown("---")

# ─── Vista previa ─────────────────────────────────────────────────────────────
st.subheader("Vista previa de artículos a exportar")
import pandas as pd

rows = []
for a in articles[:100]:
    rows.append({
        "Score": f"{a.quality_score:.0f}" if a.quality_score else "—",
        "Título": a.title[:80],
        "Autores": (a.authors[0] if a.authors else "—"),
        "Revista": (a.journal or "—")[:30],
        "Año": a.year or "—",
        "DOI": "✓" if a.doi else "—",
        "Estado": a.read_status,
        "Colección": a.collection_name,
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True, height=300)

if len(articles) > 100:
    st.caption(f"Mostrando primeros 100 de {len(articles)} artículos.")
