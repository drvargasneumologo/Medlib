"""
Página 5: Exportaciones.
CSV, JSON, RIS, BibTeX y paquete NotebookLM mejorado.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import datetime, UTC

from storage.database import get_all_articles, get_collections
from exporters.exporters import to_csv_bytes, to_json_bytes, to_ris_bytes, to_bibtex_bytes
from exporters.notebooklm_exporter import generate_notebooklm_package

st.set_page_config(page_title="Exports — MedLib", page_icon="📤", layout="wide")

# Garantizar BD inicializada
init_db()

st.title("📤 Exportaciones")

# ─── Filtros ──────────────────────────────────────────────────────────────────
st.subheader("1. Seleccionar subconjunto")

with st.form("export_filters"):
    c1, c2, c3 = st.columns(3)
    collections = [""] + get_collections()
    col_filter    = c1.selectbox("Colección", collections,
                                  format_func=lambda x: "Todas" if x == "" else x)
    status_filter = c2.selectbox("Estado", ["", "pending", "reading", "read", "priority", "included"],
                                  format_func=lambda x: "Todos" if x == "" else x)
    min_score = c3.slider("Score mínimo", 0, 100, 0, step=5)
    submitted = st.form_submit_button("🔄 Cargar artículos", type="primary")

if "export_articles" not in st.session_state or submitted:
    arts = get_all_articles(
        collection=col_filter or None,
        read_status=status_filter or None,
        min_score=min_score if min_score > 0 else None,
        limit=5000,
    )
    st.session_state["export_articles"] = arts
    st.session_state["export_col_name"] = col_filter or "medlib_export"

articles    = st.session_state.get("export_articles", [])
col_name    = st.session_state.get("export_col_name", "medlib_export")
timestamp   = datetime.now(UTC).strftime("%Y%m%d_%H%M")

if not articles:
    st.warning("No hay artículos que exportar con los filtros actuales.")
    st.stop()

st.success(f"**{len(articles)} artículos** listos para exportar.")

# ─── Formatos estándar ────────────────────────────────────────────────────────
st.subheader("2. Formatos estándar")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("#### 📊 CSV")
    st.caption("Excel, Google Sheets, pandas")
    try:
        st.download_button("⬇️ Descargar CSV", to_csv_bytes(articles),
                           f"medlib_{timestamp}.csv", "text/csv",
                           use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with c2:
    st.markdown("#### 🗂️ JSON")
    st.caption("Metadatos completos estructurados")
    try:
        st.download_button("⬇️ Descargar JSON", to_json_bytes(articles),
                           f"medlib_{timestamp}.json", "application/json",
                           use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with c3:
    st.markdown("#### 📚 RIS")
    st.caption("Zotero, Mendeley, EndNote")
    try:
        st.download_button("⬇️ Descargar RIS", to_ris_bytes(articles),
                           f"medlib_{timestamp}.ris",
                           "application/x-research-info-systems",
                           use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with c4:
    st.markdown("#### 📝 BibTeX")
    st.caption("LaTeX, Overleaf")
    try:
        st.download_button("⬇️ Descargar BibTeX", to_bibtex_bytes(articles),
                           f"medlib_{timestamp}.bib", "text/plain",
                           use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")

# ─── NotebookLM mejorado ──────────────────────────────────────────────────────
st.subheader("3. Paquete NotebookLM Optimizado")

col_nb1, col_nb2 = st.columns([2, 2])
with col_nb1:
    nb_name = st.text_input(
        "Nombre de la colección para el paquete",
        value=col_name.replace(" ", "_") or "coleccion_neumologia",
    )
    include_stats = st.checkbox("Incluir estadísticas de colección", value=True)

with col_nb2:
    st.markdown("**Contenido del paquete:**")
    st.markdown("""
    - 📋 `README.md` — Instrucciones y preguntas sugeridas para NotebookLM
    - 📊 `00_INDICE_GENERAL.md` — Tabla navegable de todos los artículos
    - 📈 `resumen_master.csv` — Datos tabulares
    - 🗂️ `metadata.json` — Metadatos completos
    - 🩺 `fichas/` — Ficha clínica PICO por artículo
    - 📁 `por_tipo/` — Agrupados por meta-análisis, ECA, guías…
    - 📉 `estadisticas/` — Resumen estadístico de la colección
    """)

# Estadísticas rápidas de la colección
with_ficha = sum(1 for a in articles if a.main_finding)
with_oa    = sum(1 for a in articles if a.open_access_status == "open")
with_pdf   = sum(1 for a in articles if a.local_pdf_path)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
col_s1.metric("Artículos", len(articles))
col_s2.metric("Con ficha clínica", with_ficha)
col_s3.metric("Acceso abierto", with_oa)
col_s4.metric("PDFs locales", with_pdf)

if with_ficha < len(articles):
    st.info(
        f"ℹ️ {len(articles) - with_ficha} artículos aún no tienen ficha clínica completa. "
        "Puedes completarlas desde **Library → Ficha Clínica** y luego regenerar el paquete."
    )

if len(articles) > 300:
    st.warning(
        f"⚠️ {len(articles)} artículos generará un ZIP grande. "
        "Considera filtrar a un subconjunto más específico."
    )

if st.button("📦 Generar paquete NotebookLM Completo", type="primary"):
    with st.spinner("Generando paquete…"):
        try:
            zip_bytes = generate_notebooklm_package(
                articles,
                collection_name=nb_name,
                include_stats=include_stats,
            )
            st.download_button(
                "⬇️ Descargar ZIP para NotebookLM",
                data=zip_bytes,
                file_name=f"notebooklm_{nb_name}_{timestamp}.zip",
                mime="application/zip",
                use_container_width=True,
            )
            st.success(
                f"✅ Paquete generado: {len(articles)} fichas + índice + estadísticas."
            )
            with st.expander("💡 Cómo usar en NotebookLM"):
                st.markdown("""
                1. Descomprime el ZIP
                2. Abre [notebooklm.google.com](https://notebooklm.google.com)
                3. Crea un nuevo Notebook
                4. Sube **primero** `00_INDICE_GENERAL.md`
                5. Sube `resumen_master.csv`
                6. Sube las fichas de `fichas/` más relevantes
                7. Opcional: sube archivos de `por_tipo/`

                **Preguntas de ejemplo:**
                - *"¿Cuáles son los hallazgos más importantes de los meta-análisis?"*
                - *"Resume la evidencia sobre [tratamiento] según los ensayos clínicos"*
                - *"¿Qué limitaciones tienen los estudios disponibles?"*
                - *"¿Cuál es la recomendación de las guías clínicas sobre [tema]?"*
                """)
        except Exception as e:
            st.error(f"Error generando paquete: {e}")

st.markdown("---")

# ─── Vista previa ─────────────────────────────────────────────────────────────
st.subheader("Vista previa")
import pandas as pd
rows = []
for a in articles[:100]:
    rows.append({
        "Score":    f"{a.quality_score:.0f}" if a.quality_score else "—",
        "Título":   a.title[:80],
        "Autores":  a.authors[0] if a.authors else "—",
        "Revista":  (a.journal or "—")[:30],
        "Año":      a.year or "—",
        "OA":       "🔓" if a.open_access_status == "open" else "—",
        "Ficha":    "✓" if a.main_finding else "—",
        "Estado":   a.read_status,
        "Colección":a.collection_name,
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)
if len(articles) > 100:
    st.caption(f"Mostrando primeros 100 de {len(articles)} artículos.")
