"""
Página 4: Revisión de duplicados potenciales.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from storage.database import (
    init_db,
    get_potential_duplicates, get_connection, update_article_fields, delete_article
)

st.set_page_config(page_title="Duplicates — MedLib", page_icon="🔀", layout="wide")

# Garantizar BD inicializada al acceder directamente a la pagina
init_db()

st.title("🔀 Revisión de Duplicados")
st.caption("Revisa grupos de artículos que el sistema detectó como potencialmente duplicados.")

# ─── Estadísticas ─────────────────────────────────────────────────────────────
groups = get_potential_duplicates()

if not groups:
    st.success("✅ No hay duplicados potenciales detectados en la biblioteca.")
    st.stop()

st.info(f"Se encontraron **{len(groups)} grupos** de artículos con posibles duplicados.")

# ─── Lista de grupos ──────────────────────────────────────────────────────────
for i, group in enumerate(groups):
    group_id = group["duplicate_group_id"]
    ids_raw = group["ids"]
    ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    count = group["cnt"]

    with st.expander(f"Grupo {i+1}: {count} artículos | ID grupo: {group_id[:20]}…", expanded=i == 0):
        # Cargar artículos del grupo
        with get_connection() as conn:
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT id, title, authors, journal, year, doi, pmid, pmcid, "
                f"source_database, quality_score, is_duplicate, abstract "
                f"FROM articles WHERE id IN ({placeholders})",
                ids
            ).fetchall()

        if not rows:
            st.warning("No se pudieron cargar los artículos de este grupo.")
            continue

        articles_data = [dict(r) for r in rows]

        # Tabla comparativa
        df = pd.DataFrame([{
            "ID": a["id"],
            "Título": (a["title"] or "")[:70],
            "Autores": (a["authors"] or "[]")[:50],
            "Revista": a["journal"] or "—",
            "Año": a["year"] or "—",
            "DOI": a["doi"] or "—",
            "PMID": a["pmid"] or "—",
            "Fuente": a["source_database"],
            "Score": f"{a['quality_score']:.0f}" if a["quality_score"] else "—",
            "Es duplicado": "✓" if a["is_duplicate"] else "❌",
        } for a in articles_data])

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Abstracts para comparación
        with st.container():
            cols = st.columns(min(len(articles_data), 3))
            for j, (col, art) in enumerate(zip(cols, articles_data[:3])):
                with col:
                    st.caption(f"**#{art['id']} — {art['source_database']}**")
                    abstract_preview = (art.get("abstract") or "Sin abstract")[:300]
                    st.markdown(f"_{abstract_preview}…_")

        # Acciones
        st.markdown("**Acciones:**")
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)

        primary_id = st.selectbox(
            "Artículo primario (conservar)",
            options=[a["id"] for a in articles_data],
            format_func=lambda x: next(
                f"ID {a['id']} — {a['title'][:40]} ({a['source_database']})"
                for a in articles_data if a["id"] == x
            ),
            key=f"primary_{group_id}"
        )

        with col_a1:
            if st.button("✅ Marcar duplicados y conservar primario", key=f"mark_{group_id}", type="primary"):
                for art in articles_data:
                    if art["id"] != primary_id:
                        update_article_fields(art["id"], {"is_duplicate": 1})
                    else:
                        update_article_fields(art["id"], {"is_duplicate": 0})
                st.success(f"Grupo resuelto. Conservado ID {primary_id}.")
                st.rerun()

        with col_a2:
            if st.button("🗑️ Eliminar todos excepto primario", key=f"delete_{group_id}"):
                for art in articles_data:
                    if art["id"] != primary_id:
                        delete_article(art["id"])
                st.success(f"Duplicados eliminados. Conservado ID {primary_id}.")
                st.rerun()

        with col_a3:
            if st.button("⏭️ Ignorar este grupo", key=f"ignore_{group_id}"):
                # Limpiar duplicate_group_id para que no aparezca más
                for art in articles_data:
                    update_article_fields(art["id"], {"duplicate_group_id": None})
                st.info("Grupo ignorado.")
                st.rerun()

        with col_a4:
            if st.button("ℹ️ Son artículos distintos", key=f"notdup_{group_id}"):
                for art in articles_data:
                    update_article_fields(art["id"], {
                        "is_duplicate": 0,
                        "duplicate_group_id": None
                    })
                st.info("Marcados como artículos distintos.")
                st.rerun()

        st.markdown("---")
