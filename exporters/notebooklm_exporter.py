"""
Exportador especializado para NotebookLM.
Genera paquetes optimizados para el flujo de trabajo de investigación médica.

ESTRUCTURA DEL PAQUETE
----------------------
{coleccion}/
  README.md                    ← Instrucciones de uso en NotebookLM
  00_INDICE_GENERAL.md         ← Tabla maestra navegable
  resumen_master.csv           ← Todos los artículos en formato tabular
  metadata.json                ← Metadatos completos estructurados
  fichas/
    {pmid}_{titulo}.md         ← Ficha clínica completa por artículo
  por_tipo/
    meta_analisis.md           ← Agrupado por tipo de evidencia
    revisiones_sistematicas.md
    ensayos_clinicos.md
    guias_clinicas.md
    otros.md
  estadisticas/
    resumen_estadistico.md     ← Estadísticas de la colección

USO EN NOTEBOOKLM
-----------------
1. Descomprime el ZIP.
2. En NotebookLM crea un nuevo Notebook.
3. Sube PRIMERO: 00_INDICE_GENERAL.md (da contexto global).
4. Sube: resumen_master.csv (permite consultas tabulares).
5. Sube selectivamente: fichas/ de los artículos más relevantes.
6. Opcional: sube los archivos por_tipo/ para consultas agrupadas.
7. Opcional: sube los PDFs si los descargaste.

PREGUNTAS SUGERIDAS PARA NOTEBOOKLM
-------------------------------------
Estas preguntas están en el README.md del paquete.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from typing import List, Optional

from models.article import Article

# Tipos de evidencia para agrupación
_TYPE_GROUPS = {
    "meta_analysis":       "meta_analisis",
    "systematic_review":   "revisiones_sistematicas",
    "rct":                 "ensayos_clinicos",
    "clinical_trial":      "ensayos_clinicos",
    "guideline":           "guias_clinicas",
    "review":              "revisiones_narrativas",
}


def generate_notebooklm_package(
    articles: List[Article],
    collection_name: str = "coleccion",
    include_stats: bool = True,
) -> bytes:
    """
    Genera el paquete ZIP completo optimizado para NotebookLM.

    Args:
        articles:        Lista de artículos a incluir.
        collection_name: Nombre de la colección (se usa como carpeta raíz).
        include_stats:   Incluir archivo de estadísticas.

    Returns:
        Bytes del archivo ZIP.
    """
    safe_name = re.sub(r"[^\w\-]", "_", collection_name)
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        root = safe_name

        # README principal con instrucciones para NotebookLM
        zf.writestr(f"{root}/README.md", _build_readme(articles, collection_name))

        # Índice general navegable
        zf.writestr(f"{root}/00_INDICE_GENERAL.md", _build_index(articles, collection_name))

        # Tabla maestra CSV
        from exporters.exporters import to_csv_bytes
        zf.writestr(f"{root}/resumen_master.csv", to_csv_bytes(articles))

        # Metadatos JSON completos
        from exporters.exporters import to_json_bytes
        zf.writestr(f"{root}/metadata.json", to_json_bytes(articles))

        # Fichas clínicas individuales
        for article in articles:
            fname = _safe_filename(article)
            zf.writestr(
                f"{root}/fichas/{fname}.md",
                _build_clinical_card(article),
            )

        # Archivos agrupados por tipo de evidencia
        type_groups = _group_by_type(articles)
        for group_key, group_articles in type_groups.items():
            if group_articles:
                zf.writestr(
                    f"{root}/por_tipo/{group_key}.md",
                    _build_type_summary(group_key, group_articles),
                )

        # Estadísticas de la colección
        if include_stats:
            zf.writestr(
                f"{root}/estadisticas/resumen_estadistico.md",
                _build_statistics(articles, collection_name),
            )

    buf.seek(0)
    return buf.read()


# ─── Builders de cada archivo ─────────────────────────────────────────────────

def _build_readme(articles: List[Article], collection_name: str) -> str:
    sources  = sorted(set(a.source_database for a in articles))
    oa_count = sum(1 for a in articles if a.open_access_status == "open")
    pdf_count = sum(1 for a in articles if a.local_pdf_path)
    types: dict = {}
    for a in articles:
        t = a.article_type or "unknown"
        types[t] = types.get(t, 0) + 1

    lines = [
        f"# 📚 Colección MedLib: {collection_name}",
        f"\n**Generado:** {datetime.now(UTC).strftime('%d %b %Y, %H:%M UTC')}  ",
        f"**Total artículos:** {len(articles)}  ",
        f"**Acceso abierto:** {oa_count}  ",
        f"**PDFs locales:** {pdf_count}  ",
        f"**Fuentes:** {', '.join(sources)}",
        "",
        "---",
        "",
        "## 🚀 Cómo usar esta colección en NotebookLM",
        "",
        "### Pasos recomendados",
        "",
        "1. **Sube primero** `00_INDICE_GENERAL.md` — da contexto global a NotebookLM",
        "2. **Sube** `resumen_master.csv` — permite preguntas tabulares",
        "3. **Sube las fichas** de `fichas/` que sean más relevantes para tu pregunta",
        "4. **Opcional:** sube archivos de `por_tipo/` para preguntas agrupadas",
        "5. **Opcional:** sube los PDFs si los tienes descargados",
        "",
        "### 💡 Preguntas sugeridas para NotebookLM",
        "",
        "Puedes hacer preguntas como estas directamente en NotebookLM:",
        "",
        "**Síntesis de evidencia:**",
        '- "¿Cuáles son los hallazgos principales de los ensayos clínicos sobre [tema]?"',
        '- "Resume la evidencia de meta-análisis disponibles en esta colección"',
        '- "¿Qué dicen las guías clínicas sobre [intervención]?"',
        "",
        "**Comparaciones:**",
        '- "Compara la eficacia de [tratamiento A] vs [tratamiento B] según los estudios"',
        '- "¿Qué outcomes se midieron más frecuentemente en estos ensayos?"',
        "",
        "**Metodología:**",
        '- "¿Qué tipos de estudio están representados? ¿Cuál es el nivel de evidencia general?"',
        '- "¿Cuáles son las poblaciones estudiadas más frecuentemente?"',
        "",
        "**Clínica práctica:**",
        '- "¿Qué limitaciones tienen los estudios disponibles para aplicación clínica?"',
        '- "¿Cuáles son los outcomes primarios más relevantes clínicamente?"',
        "",
        "**Brechas de conocimiento:**",
        '- "¿Qué preguntas clínicas quedan sin responder en la literatura disponible?"',
        '- "¿Qué poblaciones están sub-representadas en estos estudios?"',
        "",
        "---",
        "",
        "## 📁 Contenido del paquete",
        "",
        "| Archivo | Descripción |",
        "|---|---|",
        "| `00_INDICE_GENERAL.md` | Tabla navegable de todos los artículos |",
        "| `resumen_master.csv` | Datos tabulares (Excel/Google Sheets/NotebookLM) |",
        "| `metadata.json` | Metadatos completos en JSON estructurado |",
        "| `fichas/` | Ficha clínica detallada por artículo |",
        "| `por_tipo/` | Artículos agrupados por tipo de evidencia |",
        "| `estadisticas/` | Resumen estadístico de la colección |",
        "",
        "---",
        "",
        "## 📊 Distribución por tipo de evidencia",
        "",
    ]
    for t, cnt in sorted(types.items(), key=lambda x: -x[1]):
        lines.append(f"- **{t}:** {cnt} artículo(s)")

    lines += [
        "",
        "---",
        "*Generado por MedLib v0.3.0 — Biblioteca Personal de Literatura Biomédica*"
    ]
    return "\n".join(lines)


def _build_index(articles: List[Article], collection_name: str) -> str:
    """Tabla maestra navegable — el documento más útil para NotebookLM como contexto inicial."""
    lines = [
        f"# Índice General: {collection_name}",
        "",
        f"**{len(articles)} artículos** | Última actualización: "
        f"{datetime.now(UTC).strftime('%d/%m/%Y')}",
        "",
        "## Tabla de Artículos",
        "",
        "| # | Score | Título | Autores | Revista | Año | Tipo | OA | PMID |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for i, a in enumerate(sorted(articles, key=lambda x: -(x.quality_score or 0)), 1):
        score   = f"{a.quality_score:.0f}" if a.quality_score else "—"
        titulo  = (a.title or "")[:55] + ("…" if len(a.title or "") > 55 else "")
        autores = (a.authors[0] if a.authors else "—") + (" et al." if len(a.authors) > 1 else "")
        revista = (a.journal or "—")[:30]
        year    = str(a.year) if a.year else "—"
        tipo    = a.article_type or "—"
        oa      = "✓" if a.open_access_status == "open" else "—"
        pmid    = a.pmid or "—"
        lines.append(f"| {i} | {score} | {titulo} | {autores} | {revista} | {year} | {tipo} | {oa} | {pmid} |")

    lines += [
        "",
        "---",
        "",
        "## Leyenda",
        "",
        "- **Score:** Puntuación de calidad bibliográfica (0-100)",
        "- **OA:** ✓ = Acceso abierto disponible",
        "- **Tipo:** rct = Ensayo controlado aleatorio, meta_analysis, systematic_review, guideline, review",
        "",
        "## Artículos prioritarios (score ≥ 80)",
        "",
    ]

    priority = [a for a in articles if (a.quality_score or 0) >= 80]
    if priority:
        for a in sorted(priority, key=lambda x: -(x.quality_score or 0)):
            lines.append(f"- **{a.title[:70]}** — {a.to_vancouver()[:100]}")
    else:
        lines.append("*Ningún artículo alcanza score ≥ 80 con los parámetros actuales.*")

    return "\n".join(lines)


def _build_clinical_card(article: Article) -> str:
    """
    Ficha clínica completa por artículo.
    Este es el documento más rico por artículo para NotebookLM.
    """
    lines = [
        f"# {article.title}",
        "",
        "## 📖 Referencia Completa",
        "",
        f"**Vancouver:** {article.to_vancouver()}",
        "",
    ]

    # Identificadores con links
    ids = []
    if article.doi:
        ids.append(f"**DOI:** [{article.doi}](https://doi.org/{article.doi})")
    if article.pmid:
        ids.append(f"**PMID:** [{article.pmid}](https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/)")
    if article.pmcid:
        ids.append(f"**PMCID:** [{article.pmcid}](https://www.ncbi.nlm.nih.gov/pmc/articles/{article.pmcid}/)")
    if ids:
        lines.extend(ids)
        lines.append("")

    # Metadatos clave en tabla
    lines += [
        "## 📋 Metadatos",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Tipo de estudio | {article.article_type or 'No especificado'} |",
        f"| Año | {article.year or 'N/A'} |",
        f"| Revista | {article.journal or 'N/A'} |",
        f"| Idioma | {article.language or 'N/A'} |",
        f"| Acceso | {_access_label(article)} |",
        f"| Score de calidad | {article.quality_score or 'N/A'}/100 |",
        f"| Fuente de indexación | {article.source_database} |",
        f"| Citas | {article.citation_count or 'N/A'} |",
        "",
    ]

    # Abstract completo
    if article.abstract:
        lines += [
            "## 📄 Abstract",
            "",
            article.abstract,
            "",
        ]
    else:
        lines += ["## 📄 Abstract", "", "*No disponible*", ""]

    # Palabras clave
    if article.keywords or article.mesh_terms:
        lines.append("## 🏷️ Términos Clave")
        lines.append("")
        if article.mesh_terms:
            lines.append(f"**MeSH:** {' · '.join(article.mesh_terms)}")
        if article.keywords:
            lines.append(f"**Keywords:** {' · '.join(article.keywords)}")
        lines.append("")

    # Ficha clínica PICO (expandida)
    has_clinical = any([
        article.clinical_question, article.study_design, article.population,
        article.intervention, article.comparator, article.outcomes,
        article.main_finding, article.limitations, article.clinical_utility,
        article.evidence_level,
    ])

    if has_clinical:
        lines += [
            "## 🩺 Ficha Clínica",
            "",
            "### Pregunta Clínica",
            article.clinical_question or "*Pendiente de completar*",
            "",
            "### Diseño del Estudio",
            article.study_design or "*Pendiente de completar*",
            "",
            "### Población (P)",
            article.population or "*Pendiente de completar*",
            "",
            "### Intervención / Exposición (I)",
            article.intervention or "*Pendiente de completar*",
            "",
            "### Comparador (C)",
            article.comparator or "N/A",
            "",
            "### Outcomes / Desenlaces (O)",
            article.outcomes or "*Pendiente de completar*",
            "",
            "### Hallazgo Principal",
            article.main_finding or "*Pendiente de completar*",
            "",
            "### Limitaciones",
            article.limitations or "*Pendiente de completar*",
            "",
            "### Utilidad Clínica",
            article.clinical_utility or "*Pendiente de completar*",
            "",
            f"### Nivel de Evidencia: **{article.evidence_level or 'No asignado'}**",
            "",
        ]
    else:
        lines += [
            "## 🩺 Ficha Clínica",
            "",
            "> *Ficha clínica pendiente. Complétala desde la sección Library → Editar.*",
            "",
            "| Campo PICO | Estado |",
            "|---|---|",
            "| Pregunta clínica | ⏳ Pendiente |",
            "| Diseño | ⏳ Pendiente |",
            "| Población (P) | ⏳ Pendiente |",
            "| Intervención (I) | ⏳ Pendiente |",
            "| Comparador (C) | ⏳ Pendiente |",
            "| Outcomes (O) | ⏳ Pendiente |",
            "| Hallazgo principal | ⏳ Pendiente |",
            "| Limitaciones | ⏳ Pendiente |",
            "| Nivel de evidencia | ⏳ Pendiente |",
            "",
        ]

    # Notas personales
    if article.user_notes:
        lines += [
            "## 📝 Notas Personales",
            "",
            article.user_notes,
            "",
        ]

    # PDF y acceso
    lines += [
        "## 🔗 Acceso al Artículo",
        "",
    ]
    if article.local_pdf_path:
        lines.append(f"✅ **PDF local disponible:** `{article.local_pdf_path}`")
    elif article.pdf_url:
        lines.append(f"🔓 **PDF en acceso abierto:** [{article.pdf_url[:60]}]({article.pdf_url})")
    elif article.url:
        lines.append(f"🔗 **Página del artículo:** [{article.url[:60]}]({article.url})")
    else:
        lines.append("🔒 **Acceso restringido.** Consultar a través de institución o biblioteca.")

    lines += [
        "",
        "---",
        f"*Colección: {article.collection_name} | "
        f"Estado: {article.read_status} | "
        f"Recuperado: {article.date_retrieved.strftime('%Y-%m-%d') if article.date_retrieved else 'N/A'}*",
    ]
    return "\n".join(lines)


def _build_type_summary(group_key: str, articles: List[Article]) -> str:
    """Documento agrupado por tipo de evidencia."""
    type_labels = {
        "meta_analisis":          "Meta-Análisis",
        "revisiones_sistematicas":"Revisiones Sistemáticas",
        "ensayos_clinicos":       "Ensayos Clínicos",
        "guias_clinicas":         "Guías Clínicas",
        "revisiones_narrativas":  "Revisiones Narrativas",
        "otros":                  "Otros Tipos de Estudio",
    }
    label = type_labels.get(group_key, group_key.replace("_", " ").title())

    lines = [
        f"# {label} ({len(articles)} artículos)",
        "",
        f"*Generado: {datetime.now(UTC).strftime('%d/%m/%Y')}*",
        "",
        "---",
        "",
    ]

    for i, a in enumerate(sorted(articles, key=lambda x: -(x.quality_score or 0)), 1):
        lines += [
            f"## {i}. {a.title}",
            "",
            f"**Referencia:** {a.to_vancouver()}",
            "",
        ]
        if a.abstract:
            # En documentos agrupados incluir abstract corto
            abs_preview = a.abstract[:400] + ("…" if len(a.abstract) > 400 else "")
            lines += [f"**Abstract:** {abs_preview}", ""]
        if a.main_finding:
            lines += [f"**Hallazgo principal:** {a.main_finding}", ""]
        if a.evidence_level:
            lines += [f"**Nivel de evidencia:** {a.evidence_level}", ""]
        lines += ["---", ""]

    return "\n".join(lines)


def _build_statistics(articles: List[Article], collection_name: str) -> str:
    """Resumen estadístico descriptivo de la colección."""
    if not articles:
        return "# Estadísticas\n\nColección vacía."

    years = [a.year for a in articles if a.year]
    scores = [a.quality_score for a in articles if a.quality_score is not None]
    oa_count = sum(1 for a in articles if a.open_access_status == "open")
    pdf_count = sum(1 for a in articles if a.local_pdf_path)

    types: dict = defaultdict(int)
    sources: dict = defaultdict(int)
    journals: dict = defaultdict(int)
    languages: dict = defaultdict(int)
    for a in articles:
        types[a.article_type or "unknown"] += 1
        sources[a.source_database] += 1
        if a.journal:
            journals[a.journal] += 1
        if a.language:
            languages[a.language] += 1

    lines = [
        f"# Estadísticas de la Colección: {collection_name}",
        "",
        f"*Generado: {datetime.now(UTC).strftime('%d/%m/%Y')}*",
        "",
        "## Resumen General",
        "",
        f"- **Total artículos únicos:** {len(articles)}",
        f"- **Con abstract:** {sum(1 for a in articles if a.abstract)}",
        f"- **Acceso abierto:** {oa_count} ({oa_count/len(articles)*100:.1f}%)",
        f"- **PDFs descargados:** {pdf_count}",
        f"- **Con ficha clínica completa:** {sum(1 for a in articles if a.main_finding)}",
        "",
        "## Rango Temporal",
        "",
    ]

    if years:
        lines += [
            f"- **Año más antiguo:** {min(years)}",
            f"- **Año más reciente:** {max(years)}",
            f"- **Mediana de año:** {sorted(years)[len(years)//2]}",
            "",
        ]

    if scores:
        avg_score = sum(scores) / len(scores)
        lines += [
            "## Distribución de Score de Calidad",
            "",
            f"- **Score promedio:** {avg_score:.1f}/100",
            f"- **Score máximo:** {max(scores):.1f}",
            f"- **Score mínimo:** {min(scores):.1f}",
            f"- **Artículos score ≥ 80:** {sum(1 for s in scores if s >= 80)}",
            f"- **Artículos score ≥ 60:** {sum(1 for s in scores if s >= 60)}",
            "",
        ]

    lines += ["## Distribución por Tipo de Estudio", ""]
    for t, cnt in sorted(types.items(), key=lambda x: -x[1]):
        pct = cnt / len(articles) * 100
        bar = "█" * int(pct / 5)
        lines.append(f"- **{t}:** {cnt} ({pct:.1f}%) {bar}")
    lines.append("")

    lines += ["## Fuentes de Indexación", ""]
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        lines.append(f"- **{src}:** {cnt}")
    lines.append("")

    lines += ["## Revistas más frecuentes (top 10)", ""]
    top_journals = sorted(journals.items(), key=lambda x: -x[1])[:10]
    for j, cnt in top_journals:
        lines.append(f"- {j}: {cnt}")
    lines.append("")

    if languages:
        lines += ["## Idiomas", ""]
        for lang, cnt in sorted(languages.items(), key=lambda x: -x[1]):
            lines.append(f"- {lang}: {cnt}")

    return "\n".join(lines)


# ─── Utilidades ───────────────────────────────────────────────────────────────

def _group_by_type(articles: List[Article]) -> dict:
    groups: dict = defaultdict(list)
    for a in articles:
        group = _TYPE_GROUPS.get(a.article_type or "", "otros")
        groups[group].append(a)
    return dict(groups)


def _safe_filename(article: Article, max_len: int = 55) -> str:
    prefix = (
        article.pmid
        or (article.doi.replace("/", "_").replace(":", "_") if article.doi else None)
        or "art"
    )
    title_part = re.sub(r"[^\w\s-]", "", article.title or "")
    title_part = re.sub(r"\s+", "_", title_part)[:max_len]
    return f"{prefix}_{title_part}"


def _access_label(article: Article) -> str:
    if article.local_pdf_path:
        return "✅ PDF local"
    if article.open_access_status == "open":
        return "🔓 Acceso abierto"
    if article.access_type == "institutional":
        return "🏛️ Acceso institucional"
    return "🔒 Acceso restringido"
