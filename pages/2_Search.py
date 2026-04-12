"""
Página 2: Búsqueda avanzada multi-fuente.
Incluye Google Scholar (experimental) y enriquecimiento con Unpaywall.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import UTC, datetime

from services.search_service import run_search
from storage.database import get_collections, create_collection, init_db

st.set_page_config(page_title="Search — MedLib", page_icon="🔍", layout="wide")

# Garantizar BD inicializada
init_db()

st.title("🔍 Búsqueda Avanzada")
st.caption("Busca en PubMed, Europe PMC, Crossref, OpenAlex y Google Scholar (experimental).")

# ─── Formulario de búsqueda ───────────────────────────────────────────────────
with st.form("search_form"):
    st.subheader("Términos de Búsqueda")
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Query principal",
            placeholder='ej: "pulmonary fibrosis"[ti] AND ("nintedanib" OR "pirfenidone")',
            help="Soporta sintaxis PubMed: [ti], [au], [mh], AND/OR/NOT",
        )
    with col2:
        max_results = st.number_input(
            "Máx. resultados / fuente", min_value=5, max_value=500, value=50, step=10
        )

    st.subheader("Fuentes")
    c1, c2, c3, c4, c5 = st.columns(5)
    use_pubmed    = c1.checkbox("🔬 PubMed",      value=True)
    use_europepmc = c2.checkbox("🇪🇺 Europe PMC", value=True)
    use_crossref  = c3.checkbox("🔗 Crossref",    value=False)
    use_openalex  = c4.checkbox("🌐 OpenAlex",    value=False)

    # Google Scholar: desactivado por defecto, con advertencia visible
    import os
    scholar_configured = os.getenv("SCHOLAR_ENABLED", "false").lower() == "true"
    use_scholar = c5.checkbox(
        "🎓 Google Scholar",
        value=False,
        disabled=not scholar_configured,
        help=(
            "Experimental. Requiere activar en Settings y ejecutar: pip install scholarly"
            if not scholar_configured
            else "⚠️ Uso con moderación. Máx. 15 resultados recomendado."
        ),
    )
    if use_scholar:
        st.warning(
            "⚠️ **Google Scholar — uso experimental.** "
            "Metadatos incompletos, sin PMID, puede ser bloqueado por Google. "
            "Ideal solo para complementar búsquedas en PubMed."
        )

    st.subheader("Filtros")
    cf1, cf2, cf3, cf4 = st.columns(4)

    with cf1:
        year_from = st.number_input("Año desde", min_value=1900, max_value=2030, value=2019, step=1)
        year_to   = st.number_input("Año hasta", min_value=1900, max_value=2030,
                                    value=datetime.now(UTC).year, step=1)

    with cf2:
        language = st.selectbox(
            "Idioma",
            ["", "english", "spanish", "french", "german", "portuguese"],
            format_func=lambda x: "Todos" if x == "" else x.capitalize(),
        )
        article_types = st.multiselect(
            "Tipos de estudio",
            ["Clinical Trial", "Randomized Controlled Trial", "Meta-Analysis",
             "Systematic Review", "Review", "Observational Study", "Case Reports",
             "Practice Guideline", "Editorial"],
            default=[],
        )

    with cf3:
        humans_only  = st.checkbox("Solo humanos (PubMed)", value=False)
        has_abstract = st.checkbox("Solo con abstract",     value=False)
        has_fulltext = st.checkbox("Solo con texto completo", value=False)
        oa_only      = st.checkbox("Solo acceso abierto",   value=False)

    with cf4:
        deduplicate        = st.checkbox("Deduplicar resultados",       value=True)
        score              = st.checkbox("Calcular score de calidad",   value=True)
        save_to_db         = st.checkbox("Guardar en biblioteca",       value=True)
        enrich_unpaywall   = st.checkbox(
            "🔓 Enriquecer con Unpaywall (PDFs OA)",
            value=os.getenv("UNPAYWALL_ENABLED", "true").lower() == "true",
            help="Consulta Unpaywall para encontrar PDFs en acceso abierto por DOI.",
        )

    st.subheader("Colección de Destino")
    col_c1, col_c2 = st.columns(2)
    collections = get_collections()
    collection_select = col_c1.selectbox(
        "Colección existente",
        options=collections,
        index=0 if collections else None,
    )
    new_collection = col_c2.text_input("O crear nueva colección", placeholder="Nombre")

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
    if use_scholar:   sources.append("google_scholar")

    if not sources:
        st.warning("Selecciona al menos una fuente.")
        st.stop()

    target_collection = new_collection.strip() or collection_select or "default"
    if new_collection.strip():
        create_collection(new_collection.strip())

    date_from_str = f"{year_from}/01/01" if year_from else None
    date_to_str   = f"{year_to}/12/31"   if year_to   else None

    progress = st.progress(0, text="Iniciando búsqueda…")
    status   = st.empty()

    def cb(pct, msg):
        progress.progress(pct, text=msg)
        status.caption(msg)

    with st.spinner("Buscando…"):
        result = run_search(
            query=query,
            sources=sources,
            collection_name=target_collection,
            max_results=int(max_results),
            date_from=date_from_str,
            date_to=date_to_str,
            year_from=int(year_from) if year_from else None,
            year_to=int(year_to)   if year_to   else None,
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
            progress_callback=cb,
        )

    # Enriquecimiento Unpaywall (post-búsqueda, en lote)
    if enrich_unpaywall and result["articles"]:
        contact_email = os.getenv("CONTACT_EMAIL", "")
        if contact_email:
            with st.spinner("🔓 Consultando Unpaywall para PDFs en acceso abierto…"):
                from connectors.unpaywall import enrich_article_with_unpaywall
                from storage.database import update_article_fields, get_connection
                enriched = 0
                for a in result["articles"]:
                    if a.doi:
                        changed = enrich_article_with_unpaywall(a)
                        if changed and a.id:
                            update_article_fields(a.id, {
                                "pdf_url": a.pdf_url,
                                "open_access_status": a.open_access_status,
                                "access_type": a.access_type,
                                "landing_page_url": a.landing_page_url,
                            })
                            enriched += 1
            if enriched:
                st.success(f"🔓 Unpaywall: {enriched} artículos enriquecidos con información OA.")
        else:
            st.info("ℹ️ Unpaywall requiere CONTACT_EMAIL en Settings para funcionar.")

    progress.empty()
    status.empty()

    # ─── Resumen de resultados ────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Resultados brutos",     result["total_raw"])
    c2.metric("Únicos",               result["total_unique"])
    c3.metric("Duplicados detectados", result["duplicates_found"])
    c4.metric("Guardados en BD",       result["total_saved"])

    if result["errors"]:
        with st.expander("⚠️ Errores durante la búsqueda"):
            for err in result["errors"]:
                st.error(err)

    articles = result["articles"]
    if not articles:
        st.warning("No se encontraron resultados. Prueba con términos más generales.")
        st.stop()

    st.success(f"✅ {len(articles)} artículos en colección **{target_collection}**")
    st.session_state["last_search_results"] = articles

    # ─── Tabla de resultados ──────────────────────────────────────────────────
    st.subheader("Resultados")

    rows = []
    for a in articles:
        rows.append({
            "Score":   f"{a.quality_score:.0f}" if a.quality_score else "—",
            "Título":  a.title[:85] + ("…" if len(a.title) > 85 else ""),
            "Autores": (a.authors[0] if a.authors else "—")
                       + (" et al." if len(a.authors) > 1 else ""),
            "Revista": (a.journal or "—")[:35],
            "Año":     a.year or "—",
            "Tipo":    a.article_type or "—",
            "Fuente":  a.source_database,
            "DOI":     "✓" if a.doi else "—",
            "OA":      "🔓" if a.open_access_status == "open" else "🔒",
            "PDF":     "📄" if a.pdf_url else "—",
        })

    df = pd.DataFrame(rows)

    with st.expander("🔽 Filtros rápidos"):
        cf1, cf2, cf3 = st.columns(3)
        ft = cf1.multiselect("Tipo",   df["Tipo"].unique().tolist())
        fs = cf2.multiselect("Fuente", df["Fuente"].unique().tolist())
        fo = cf3.checkbox("Solo acceso abierto")
        if ft: df = df[df["Tipo"].isin(ft)]
        if fs: df = df[df["Fuente"].isin(fs)]
        if fo: df = df[df["OA"] == "🔓"]

    st.dataframe(df, use_container_width=True, hide_index=True, height=420)

    # ─── Detalle de artículo ──────────────────────────────────────────────────
    st.subheader("Vista detallada")
    options = [f"{i+1}. {a.title[:80]}" for i, a in enumerate(articles)]
    idx = st.selectbox("Selecciona artículo:", range(len(articles)),
                       format_func=lambda i: options[i])

    if idx is not None:
        a = articles[idx]
        _show_detail(a)


def _show_detail(a):
    from services.scoring_service import score_explanation
    from datetime import datetime

    st.markdown(
        f"<div style='background:#f0f7ff;border-left:4px solid #1a6ca8;"
        f"padding:1rem;border-radius:6px;margin-bottom:1rem'>"
        f"<div style='font-size:1.05rem;font-weight:600;color:#1a4a6e'>{a.title}</div>"
        f"<div style='font-size:0.82rem;color:#5a7fa0;margin-top:0.4rem'>"
        f"{('; '.join(a.authors))[:120]}</div></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**Revista:** {a.journal or '—'}")
    c2.markdown(f"**Año:** {a.year or '—'}")
    c3.markdown(f"**Tipo:** {a.article_type or '—'}")
    c4.markdown(f"**Score:** {a.quality_score or '—'}/100")

    id_cols = st.columns(4)
    if a.doi:        id_cols[0].markdown(f"**DOI:** [{a.doi}](https://doi.org/{a.doi})")
    if a.pmid:       id_cols[1].markdown(f"**PMID:** [{a.pmid}](https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/)")
    if a.pmcid:      id_cols[2].markdown(f"**PMCID:** {a.pmcid}")
    if a.pdf_url:    id_cols[3].markdown(f"**PDF OA:** [Abrir]({a.pdf_url})")
    elif a.url:      id_cols[3].markdown(f"**Artículo:** [Ver]({a.url})")

    if a.abstract:
        with st.expander("📄 Abstract", expanded=True):
            st.write(a.abstract)

    if a.mesh_terms: st.markdown(f"**MeSH:** {', '.join(a.mesh_terms[:10])}")
    if a.keywords:   st.markdown(f"**Keywords:** {', '.join(a.keywords[:10])}")

    if a.quality_score is not None:
        with st.expander("📊 Explicación del Score"):
            expl = score_explanation(a, current_year=datetime.now(UTC).year)
            for k, v in expl.items():
                st.markdown(f"- **{k}:** {v}")
