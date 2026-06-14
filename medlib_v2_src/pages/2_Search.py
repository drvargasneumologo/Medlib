"""
Página 2: Búsqueda avanzada.
Búsqueda en múltiples fuentes con filtros clínicos.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import UTC, datetime

from services.search_service import run_search
from storage.database import get_collections, create_collection

st.set_page_config(page_title="Search — MedLib", page_icon="🔍", layout="wide")

st.title("🔍 Búsqueda Avanzada")
st.caption("Busca en PubMed, Europe PMC, Crossref y OpenAlex con un solo formulario.")

# ─── Formulario de búsqueda ───────────────────────────────────────────────────
with st.form("search_form"):
    st.subheader("Términos de Búsqueda")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Query principal",
            placeholder='ej: "pulmonary fibrosis"[ti] AND ("nintedanib" OR "pirfenidone")',
            help="Soporta sintaxis PubMed: campos [ti], [au], [mh], operadores AND/OR/NOT"
        )
    with col2:
        max_results = st.number_input("Máx. resultados / fuente", min_value=5, max_value=500, value=50, step=10)

    st.subheader("Fuentes")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    use_pubmed     = col_s1.checkbox("PubMed", value=True)
    use_europepmc  = col_s2.checkbox("Europe PMC", value=True)
    use_crossref   = col_s3.checkbox("Crossref", value=False)
    use_openalex   = col_s4.checkbox("OpenAlex", value=False)

    st.subheader("Filtros")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        year_from = st.number_input("Año desde", min_value=1900, max_value=2030, value=2019, step=1)
        year_to   = st.number_input("Año hasta", min_value=1900, max_value=2030, value=datetime.now(UTC).year, step=1)

    with col_f2:
        language = st.selectbox(
            "Idioma",
            ["", "english", "spanish", "french", "german", "portuguese", "italian"],
            format_func=lambda x: "Todos los idiomas" if x == "" else x.capitalize()
        )
        article_types = st.multiselect(
            "Tipos de estudio",
            ["Clinical Trial", "Randomized Controlled Trial", "Meta-Analysis",
             "Systematic Review", "Review", "Observational Study", "Case Reports",
             "Practice Guideline", "Editorial"],
            default=[]
        )

    with col_f3:
        humans_only   = st.checkbox("Solo humanos (PubMed)", value=False)
        has_abstract  = st.checkbox("Solo con abstract", value=False)
        has_fulltext  = st.checkbox("Solo con texto completo", value=False)
        oa_only       = st.checkbox("Solo acceso abierto", value=False)

    with col_f4:
        deduplicate = st.checkbox("Deduplicar resultados", value=True)
        score       = st.checkbox("Calcular score de calidad", value=True)
        save_to_db  = st.checkbox("Guardar en biblioteca", value=True)

    st.subheader("Colección de Destino")
    col_c1, col_c2 = st.columns([2, 2])
    collections = get_collections()
    
    with col_c1:
        collection_select = st.selectbox(
            "Colección existente",
            options=collections,
            index=0 if collections else None
        )
    with col_c2:
        new_collection = st.text_input(
            "O crear nueva colección",
            placeholder="Nombre de nueva colección"
        )

    submitted = st.form_submit_button("🔍 Ejecutar Búsqueda", type="primary", use_container_width=True)

# ─── Ejecución ────────────────────────────────────────────────────────────────
if submitted:
    if not query.strip():
        st.warning("Por favor introduce un término de búsqueda.")
        st.stop()

    sources = []
    if use_pubmed:    sources.append("pubmed")
    if use_europepmc: sources.append("europepmc")
    if use_crossref:  sources.append("crossref")
    if use_openalex:  sources.append("openalex")

    if not sources:
        st.warning("Selecciona al menos una fuente.")
        st.stop()

    # Determinar colección
    target_collection = new_collection.strip() if new_collection.strip() else (collection_select or "default")
    if new_collection.strip():
        create_collection(new_collection.strip())

    date_from_str = f"{year_from}/01/01" if year_from else None
    date_to_str   = f"{year_to}/12/31" if year_to else None

    progress_bar  = st.progress(0, text="Iniciando búsqueda...")
    status_text   = st.empty()

    def progress_callback(pct, msg):
        progress_bar.progress(pct, text=msg)
        status_text.caption(msg)

    with st.spinner("Buscando…"):
        result = run_search(
            query=query,
            sources=sources,
            collection_name=target_collection,
            max_results=int(max_results),
            date_from=date_from_str,
            date_to=date_to_str,
            year_from=int(year_from) if year_from else None,
            year_to=int(year_to) if year_to else None,
            language=language or None,
            article_types=article_types or None,
            open_access_only=oa_only,
            humans_only=humans_only,
            has_abstract=has_abstract,
            has_fulltext=has_fulltext,
            deduplicate=deduplicate,
            score=score,
            save_to_db=save_to_db,
            current_year=datetime.now(UTC).year,
            progress_callback=progress_callback,
        )

    progress_bar.empty()
    status_text.empty()

    # ─── Resultados ───────────────────────────────────────────────────────────
    st.markdown("---")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("Resultados brutos", result["total_raw"])
    col_r2.metric("Únicos", result["total_unique"])
    col_r3.metric("Duplicados detectados", result["duplicates_found"])
    col_r4.metric("Guardados en BD", result["total_saved"])

    if result["errors"]:
        with st.expander("⚠️ Errores durante la búsqueda"):
            for err in result["errors"]:
                st.error(err)

    articles = result["articles"]

    if not articles:
        st.warning("No se encontraron resultados. Prueba con términos más generales.")
        st.stop()

    st.success(f"✅ {len(articles)} artículos únicos encontrados en colección **{target_collection}**")

    # Guardar en session_state para referencia
    st.session_state["last_search_results"] = articles
    st.session_state["last_query"] = query

    # ─── Vista tabular ────────────────────────────────────────────────────────
    st.subheader("Resultados")

    rows = []
    for a in articles:
        rows.append({
            "Score": f"{a.quality_score:.0f}" if a.quality_score else "—",
            "Título": a.title[:90] + ("…" if len(a.title) > 90 else ""),
            "Autores": a.authors_str[:50] if a.authors else "—",
            "Revista": (a.journal or "—")[:35],
            "Año": a.year or "—",
            "Tipo": a.article_type or "—",
            "Fuente": a.source_database,
            "DOI": "✓" if a.doi else "—",
            "Abstract": "✓" if a.abstract else "✗",
            "OA": "🔓" if a.open_access_status == "open" else "🔒",
            "PDF": "✓" if a.pdf_url else "—",
        })

    df = pd.DataFrame(rows)

    # Filtros rápidos
    with st.expander("🔽 Filtros rápidos de resultados"):
        col_f1, col_f2, col_f3 = st.columns(3)
        filter_type = col_f1.multiselect("Tipo", df["Tipo"].unique().tolist())
        filter_source = col_f2.multiselect("Fuente", df["Fuente"].unique().tolist())
        only_oa = col_f3.checkbox("Solo acceso abierto")

        if filter_type:
            df = df[df["Tipo"].isin(filter_type)]
        if filter_source:
            df = df[df["Fuente"].isin(filter_source)]
        if only_oa:
            df = df[df["OA"] == "🔓"]

    st.dataframe(df, use_container_width=True, hide_index=True, height=450)

    # ─── Detalle de artículo ──────────────────────────────────────────────────
    st.subheader("Vista detallada")
    article_titles = [f"{i+1}. {a.title[:80]}" for i, a in enumerate(articles)]
    selected_idx = st.selectbox("Selecciona un artículo para ver detalle:", range(len(articles)),
                                format_func=lambda i: article_titles[i])

    if selected_idx is not None:
        sel = articles[selected_idx]
        _show_article_detail(sel)


def _show_article_detail(a):
    """Muestra el detalle completo de un artículo."""
    from services.scoring_service import score_explanation
    from datetime import UTC, datetime

    st.markdown(f"""
    <div style="background:#f0f7ff; border-left:4px solid #1a6ca8; padding:1rem; border-radius:6px; margin-bottom:1rem;">
        <div style="font-size:1.05rem; font-weight:600; color:#1a4a6e;">{a.title}</div>
        <div style="font-size:0.82rem; color:#5a7fa0; margin-top:0.4rem;">{a.authors_str[:120]}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**Revista:** {a.journal or '—'}")
    c2.markdown(f"**Año:** {a.year or '—'}")
    c3.markdown(f"**Tipo:** {a.article_type or '—'}")
    c4.markdown(f"**Score:** {a.quality_score or '—'}/100")

    id_cols = st.columns(4)
    if a.doi:
        id_cols[0].markdown(f"**DOI:** [{a.doi}](https://doi.org/{a.doi})")
    if a.pmid:
        id_cols[1].markdown(f"**PMID:** [{a.pmid}](https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/)")
    if a.pmcid:
        id_cols[2].markdown(f"**PMCID:** {a.pmcid}")
    id_cols[3].markdown(f"**Acceso:** {a.access_type or '—'}")

    if a.abstract:
        with st.expander("📄 Abstract", expanded=True):
            st.write(a.abstract)

    if a.mesh_terms:
        st.markdown(f"**MeSH:** {', '.join(a.mesh_terms[:10])}")
    if a.keywords:
        st.markdown(f"**Keywords:** {', '.join(a.keywords[:10])}")

    if a.quality_score is not None:
        with st.expander("📊 Explicación del Score"):
            expl = score_explanation(a, current_year=datetime.now(UTC).year)
            for k, v in expl.items():
                st.markdown(f"- **{k}:** {v}")
