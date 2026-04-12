"""
P�gina 6: Auditoría de la biblioteca.
Detecta problemas de calidad, metadatos incompletos y duplicados.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from storage.database import (
    get_audit_report, get_all_articles, update_article_fields, get_connection
)

st.set_page_config(page_title="Audit — MedLib", page_icon="🔎", layout="wide")

st.title("🔎 Auditoría de Calidad")
st.caption("Detecta problemas en tu biblioteca para mantener metadatos limpios y completos.")

# ─── Reporte de auditoría ─────────────────────────────────────────────────────
report = get_audit_report()

st.subheader("Resumen de Problemas")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sin DOI",       report["missing_doi"],
            help="Artículos sin identificador DOI")
col2.metric("Sin PMID",      report["missing_pmid"],
            help="Normal para fuentes no-PubMed")
col3.metric("Sin Abstract",  report["missing_abstract"],
            help="Artículos sin texto de resumen")
col4.metric("Sin PDF local", report["missing_pdf"],
            help="Artículos sin PDF descargado localmente")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Preprints",         report["preprints"],
            help="No revisados por pares")
col6.metric("Revistas dudosas",  report["predatory_journals"],
            help="Potencialmente predatorias")
col7.metric("Errores de parseo", report["parsing_errors"])
col8.metric("Grupos duplicados", report["duplicate_groups"],
            help="Grupos pendientes de revisión")

st.markdown("---")

# ─── Artículos problemáticos ──────────────────────────────────────────────────
st.subheader("Artículos con Problemas Detectados")

problem_type = st.selectbox("Ver artículos con:", [
    "Sin DOI",
    "Sin Abstract",
    "Sin PMID",
    "Preprints",
    "Metadatos incompletos",
    "Revistas dudosas",
    "Con errores de parseo",
])

all_articles = get_all_articles(limit=5000)

filtered = []
if problem_type == "Sin DOI":
    filtered = [a for a in all_articles if not a.doi]
elif problem_type == "Sin Abstract":
    filtered = [a for a in all_articles if not a.abstract]
elif problem_type == "Sin PMID":
    filtered = [a for a in all_articles if not a.pmid]
elif problem_type == "Preprints":
    filtered = [a for a in all_articles if a.flag_preprint]
elif problem_type == "Metadatos incompletos":
    filtered = [a for a in all_articles if a.flag_incomplete_metadata]
elif problem_type == "Revistas dudosas":
    filtered = [a for a in all_articles if a.flag_potential_predatory]
elif problem_type == "Con errores de parseo":
    filtered = [a for a in all_articles if a.flag_parsing_error]

if filtered:
    st.markdown(f"**{len(filtered)} artículos** con problema: _{problem_type}_")
    rows = []
    for a in filtered:
        rows.append({
            "ID":        a.id,
            "Título":    a.title[:80],
            "Fuente":    a.source_database,
            "Año":       a.year or "—",
            "DOI":       a.doi or "❌",
            "PMID":      a.pmid or "❌",
            "Abstract":  "✓" if a.abstract else "❌",
            "Colección": a.collection_name,
            "Score":     f"{a.quality_score:.0f}" if a.quality_score else "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
else:
    st.success(f"✅ No hay artículos con '{problem_type}'.")

st.markdown("---")

# ─── Acciones de mantenimiento ────────────────────────────────────────────────
st.subheader("Acciones de Mantenimiento")

col_a1, col_a2 = st.columns(2)

with col_a1:
    st.markdown("#### Recalcular scores")
    st.caption("Recalcula el score de calidad para todos los artículos.")
    if st.button("🔄 Recalcular todos los scores", type="secondary"):
        from services.scoring_service import score_batch
        from datetime import datetime
        all_arts = get_all_articles(limit=10000)
        score_batch(all_arts, current_year=datetime.utcnow().year)
        count = 0
        for a in all_arts:
            if a.id:
                update_article_fields(a.id, {"quality_score": a.quality_score})
                count += 1
        st.success(f"✅ Scores recalculados para {count} artículos.")
        st.rerun()

with col_a2:
    st.markdown("#### Re-deduplicar biblioteca")
    st.caption("Ejecuta el algoritmo de deduplicación sobre toda la biblioteca.")
    if st.button("🔀 Re-deduplicar biblioteca", type="secondary"):
        from services.dedup_service import deduplicate_articles
        import json

        all_arts = get_all_articles(limit=10000)
        _, pairs = deduplicate_articles(all_arts)

        updated = 0
        for pair in pairs:
            # Buscar artículo por fingerprint y marcarlo como duplicado
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT id FROM articles WHERE fingerprint = ?",
                    (pair["duplicate_fingerprint"],),
                ).fetchall()
                for row in rows:
                    update_article_fields(row["id"], {
                        "is_duplicate":       1,
                        "duplicate_group_id": pair["primary_fingerprint"],
                    })
                    updated += 1

        st.success(f"✅ {len(pairs)} pares detectados. {updated} registros marcados como duplicados.")
        st.rerun()

st.markdown("---")
st.subheader("Log de actividad")
try:
    with open("data/medlib.log", "r", encoding="utf-8") as f:
        log_lines = f.readlines()
    last_lines = log_lines[-50:]
    st.code("".join(last_lines), language="text")
except FileNotFoundError:
    st.info("No hay log disponible todavía.")
