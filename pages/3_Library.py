"""
Página 3: Biblioteca — visualización y gestión de artículos almacenados.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import UTC, datetime

from storage.database import (
    get_all_articles, get_collections, update_article_fields, delete_article, get_article_by_id
)
from services.scoring_service import score_explanation

st.set_page_config(page_title="Library — MedLib", page_icon="📚", layout="wide")

st.title("📚 Biblioteca")

# ─── Filtros de biblioteca ────────────────────────────────────────────────────
with st.expander("🔽 Filtros", expanded=True):
    col1, col2, col3, col4 = st.columns(4)

    collections = [""] + get_collections()
    collection_filter = col1.selectbox(
        "Colección",
        collections,
        format_func=lambda x: "Todas" if x == "" else x
    )
    status_filter = col2.selectbox(
        "Estado de lectura",
        ["", "pending", "reading", "read", "priority", "included"],
        format_func=lambda x: {
            "": "Todos", "pending": "⏳ Pendiente", "reading": "📖 Leyendo",
            "read": "✅ Leído", "priority": "⭐ Prioritario", "included": "📌 Incluido"
        }.get(x, x)
    )

    col3a, col3b = col3.columns(2)
    year_from = col3a.number_input("Año desde", min_value=1900, max_value=2030, value=2000, step=1)
    year_to   = col3b.number_input("Hasta", min_value=1900, max_value=2030, value=datetime.now(UTC).year, step=1)

    source_filter = col4.selectbox(
        "Fuente",
        ["", "pubmed", "europepmc_med", "europepmc_pmc", "crossref", "openalex"],
        format_func=lambda x: "Todas" if x == "" else x
    )

    col5, col6, col7 = st.columns(3)
    min_score = col5.slider("Score mínimo", 0, 100, 0, step=5)
    search_text = col6.text_input("Buscar en título/abstract/autores", placeholder="texto libre…")
    limit = col7.number_input("Límite de resultados", min_value=10, max_value=2000, value=200, step=50)

# ─── Cargar artículos ─────────────────────────────────────────────────────────
articles = get_all_articles(
    collection=collection_filter or None,
    read_status=status_filter or None,
    year_from=int(year_from),
    year_to=int(year_to),
    source=source_filter or None,
    min_score=min_score if min_score > 0 else None,
    search_text=search_text or None,
    limit=int(limit),
)

st.markdown(f"**{len(articles)} artículos** encontrados con los filtros actuales.")

if not articles:
    st.info("No hay artículos que coincidan con los filtros. Realiza una búsqueda primero.")
    st.stop()

# ─── Tabla principal ──────────────────────────────────────────────────────────
rows = []
for a in articles:
    score_str = f"{a.quality_score:.0f}" if a.quality_score is not None else "—"
    rows.append({
        "ID": a.id,
        "Score": score_str,
        "Título": a.title[:85] + ("…" if len(a.title) > 85 else ""),
        "Autores": (a.authors[0] if a.authors else "—") + (" et al." if len(a.authors) > 1 else ""),
        "Revista": (a.journal or "—")[:30],
        "Año": a.year or "—",
        "Tipo": a.article_type or "—",
        "Fuente": a.source_database,
        "Estado": a.read_status,
        "OA": "🔓" if a.open_access_status == "open" else "🔒",
        "PDF": "📄" if a.local_pdf_path else ("🔗" if a.pdf_url else "—"),
        "DOI": "✓" if a.doi else "—",
        "Colección": a.collection_name or "—",
    })

df = pd.DataFrame(rows)

# Ordenar por score por defecto
df = df.sort_values("Score", ascending=False, key=lambda x: pd.to_numeric(x, errors="coerce"))

selection = st.dataframe(
    df.drop(columns=["ID"]),
    use_container_width=True,
    hide_index=True,
    height=380,
)

# ─── Panel de edición por artículo ────────────────────────────────────────────
st.markdown("---")
st.subheader("Gestión de Artículo")

article_options = {f"{a.id} — {a.title[:70]}": a.id for a in articles}
selected_label = st.selectbox("Selecciona un artículo:", list(article_options.keys()))
selected_id = article_options.get(selected_label)

if selected_id:
    article = get_article_by_id(selected_id)
    if not article:
        st.error("Artículo no encontrado.")
        st.stop()

    # ─── Detalle ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Metadatos", "✏️ Editar", "🩺 Ficha Clínica", "📊 Score"])

    with tab1:
        st.markdown(f"### {article.title}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Autores:** {article.authors_str or '—'}")
            st.markdown(f"**Revista:** {article.journal or '—'}")
            st.markdown(f"**Año:** {article.year or '—'} | **Vol:** {article.volume or '—'} | **Issue:** {article.issue or '—'} | **Págs:** {article.pages or '—'}")
            st.markdown(f"**Idioma:** {article.language or '—'} | **Tipo:** {article.article_type or '—'}")
            st.markdown(f"**Fuente BD:** {article.source_database}")
            st.markdown(f"**Colección:** {article.collection_name}")
        with c2:
            if article.doi:
                st.markdown(f"**DOI:** [{article.doi}](https://doi.org/{article.doi})")
            if article.pmid:
                st.markdown(f"**PMID:** [{article.pmid}](https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/)")
            if article.pmcid:
                st.markdown(f"**PMCID:** {article.pmcid}")
            st.markdown(f"**Acceso:** {article.access_type or '—'}")
            if article.pdf_url:
                st.markdown(f"**PDF URL:** [{article.pdf_url[:60]}...]({article.pdf_url})")
            if article.citation_count is not None:
                st.markdown(f"**Citas:** {article.citation_count}")
            st.markdown(f"**Score:** {article.quality_score or '—'}/100")

        if article.abstract:
            with st.expander("Abstract"):
                st.write(article.abstract)

        if article.mesh_terms:
            st.markdown(f"**MeSH:** {', '.join(article.mesh_terms[:10])}")
        if article.keywords:
            st.markdown(f"**Keywords:** {', '.join(article.keywords[:10])}")
        if article.affiliation:
            st.markdown(f"**Afiliación:** {article.affiliation[:150]}")

    with tab2:
        st.markdown("#### Editar estado y notas")
        col_e1, col_e2, col_e3 = st.columns(3)

        new_status = col_e1.selectbox(
            "Estado de lectura",
            ["pending", "reading", "read", "priority", "included"],
            index=["pending", "reading", "read", "priority", "included"].index(article.read_status),
            key=f"status_{selected_id}"
        )

        all_collections = get_collections()
        new_collection = col_e2.selectbox(
            "Colección",
            all_collections,
            index=all_collections.index(article.collection_name) if article.collection_name in all_collections else 0,
            key=f"col_{selected_id}"
        )

        tags_input = col_e3.text_input(
            "Tags (separados por coma)",
            value=article.tags_str,
            key=f"tags_{selected_id}"
        )

        notes = st.text_area(
            "Notas del usuario",
            value=article.user_notes or "",
            height=120,
            key=f"notes_{selected_id}"
        )

        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("💾 Guardar", key=f"save_{selected_id}", type="primary"):
                tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
                import json
                update_article_fields(selected_id, {
                    "read_status": new_status,
                    "collection_name": new_collection,
                    "user_notes": notes,
                    "tags": json.dumps(tags_list),
                })
                st.success("✅ Cambios guardados.")
                st.rerun()

    with tab3:
        st.markdown("#### Ficha Clínica")
        st.caption("Completa los campos para preparar resúmenes de alta calidad.")

        with st.form(f"clinical_form_{selected_id}"):
            cq = st.text_input("Pregunta clínica / PICO", value=article.clinical_question or "")
            sd = st.text_input("Diseño del estudio", value=article.study_design or "")
            
            col_p1, col_p2 = st.columns(2)
            pop = col_p1.text_area("Población", value=article.population or "", height=80)
            intv = col_p2.text_area("Intervención / Exposición", value=article.intervention or "", height=80)
            
            col_p3, col_p4 = st.columns(2)
            comp = col_p3.text_area("Comparador", value=article.comparator or "", height=80)
            outc = col_p4.text_area("Outcomes", value=article.outcomes or "", height=80)

            finding = st.text_area("Hallazgo principal", value=article.main_finding or "", height=80)
            lims = st.text_area("Limitaciones", value=article.limitations or "", height=80)
            
            col_p5, col_p6 = st.columns(2)
            utility = col_p5.text_area("Utilidad clínica", value=article.clinical_utility or "", height=80)
            ev_level = col_p6.selectbox(
                "Nivel de evidencia",
                ["", "Ia", "Ib", "IIa", "IIb", "III", "IV", "V"],
                index=["", "Ia", "Ib", "IIa", "IIb", "III", "IV", "V"].index(article.evidence_level)
                      if article.evidence_level in ["", "Ia", "Ib", "IIa", "IIb", "III", "IV", "V"] else 0,
            )

            if st.form_submit_button("💾 Guardar Ficha Clínica", type="primary"):
                update_article_fields(selected_id, {
                    "clinical_question": cq,
                    "study_design": sd,
                    "population": pop,
                    "intervention": intv,
                    "comparator": comp,
                    "outcomes": outc,
                    "main_finding": finding,
                    "limitations": lims,
                    "clinical_utility": utility,
                    "evidence_level": ev_level or None,
                })
                st.success("✅ Ficha clínica guardada.")

    with tab4:
        if article.quality_score is not None:
            st.metric("Score de Calidad", f"{article.quality_score:.1f} / 100")
            expl = score_explanation(article, current_year=datetime.now(UTC).year)
            for k, v in expl.items():
                color = "green" if "+" in str(v) else "gray"
                st.markdown(f"- :{color}[**{k}:**] {v}")
        else:
            st.info("Score no calculado. Realiza una nueva búsqueda con scoring activado.")

    # ─── Eliminar artículo ────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚠️ Zona de peligro"):
        if st.button("🗑️ Eliminar este artículo de la biblioteca", type="secondary"):
            delete_article(selected_id)
            st.success("Artículo eliminado.")
            st.rerun()
