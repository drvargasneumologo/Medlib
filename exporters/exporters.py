"""
Exportadores de biblioteca.
CSV, JSON, RIS, BibTeX y formato NotebookLM.

NOTAS DE DISEÑO
---------------
- to_csv_bytes: usa model_dump() (retorna objetos Python nativos) y serializa
  manualmente los campos datetime para evitar que csv.DictWriter llame str()
  sobre objetos datetime con formato no estándar.
- to_json_bytes: usa model_dump(mode='json') que serializa datetime como
  ISO 8601 strings directamente.
- generate_notebooklm_zip: genera un ZIP autocontenido con fichas Markdown
  por artículo, listo para cargar en NotebookLM como fuentes.
"""
from __future__ import annotations

import csv
import html
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from typing import List, Optional

from models.article import Article


# ─── CSV ──────────────────────────────────────────────────────────────────────

_CSV_FIELDS = [
    "id", "title", "authors", "journal", "year", "volume", "issue", "pages",
    "doi", "pmid", "pmcid", "abstract", "keywords", "mesh_terms",
    "article_type", "language", "source_database", "quality_score",
    "open_access_status", "access_type", "pdf_url", "url",
    "collection_name", "read_status", "user_notes", "tags",
    "citation_count", "date_retrieved", "affiliation",
]


def to_csv_bytes(articles: List[Article]) -> bytes:
    """
    Exporta lista de artículos a CSV como bytes UTF-8 con BOM.
    El BOM permite apertura correcta en Microsoft Excel.

    Serialización de campos especiales:
    - Listas (authors, keywords, etc.): separadas por "; "
    - datetime: ISO 8601 string
    - None: string vacío
    """
    if not articles:
        return b""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()

    for a in articles:
        row = a.model_dump()

        # Serializar listas como strings
        row["authors"]    = a.authors_str
        row["keywords"]   = a.keywords_str
        row["mesh_terms"] = a.mesh_str
        row["tags"]       = a.tags_str

        # Serializar datetimes explícitamente (model_dump() retorna objetos Python)
        row["date_retrieved"] = (
            a.date_retrieved.isoformat() if a.date_retrieved else ""
        )
        if row.get("pdf_download_date") and hasattr(row["pdf_download_date"], "isoformat"):
            row["pdf_download_date"] = row["pdf_download_date"].isoformat()

        # Convertir None a string vacío para CSV
        writer.writerow({k: ("" if row.get(k) is None else row.get(k, "")) for k in _CSV_FIELDS})

    return output.getvalue().encode("utf-8-sig")  # BOM para Excel


# ─── JSON ─────────────────────────────────────────────────────────────────────

def to_json_bytes(articles: List[Article]) -> bytes:
    """
    Exporta a JSON estructurado.
    Usa model_dump(mode='json') que serializa datetime como ISO 8601.
    """
    data = {
        "export_date":    datetime.now(UTC).isoformat(),
        "total_articles": len(articles),
        "articles":       [a.model_dump(mode="json") for a in articles],
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


# ─── RIS ──────────────────────────────────────────────────────────────────────

_ARTICLE_TYPE_TO_RIS = {
    "meta_analysis":    "JOUR",
    "systematic_review":"JOUR",
    "rct":              "JOUR",
    "clinical_trial":   "JOUR",
    "review":           "JOUR",
    "journal_article":  "JOUR",
    "case_report":      "CASE",
    "book_chapter":     "CHAP",
    "conference":       "CONF",
    "preprint":         "UNPB",
    "dissertation":     "THES",
    "report":           "RPRT",
    "editorial":        "EDBOOK",
    "letter":           "PCOMM",
    "guideline":        "GOVDOC",
}


def to_ris_bytes(articles: List[Article]) -> bytes:
    """Exporta a formato RIS (compatible con Zotero, Mendeley, EndNote)."""
    if not articles:
        return b""

    output = io.StringIO()
    for a in articles:
        ris_type = _ARTICLE_TYPE_TO_RIS.get(a.article_type or "", "JOUR")
        output.write(f"TY  - {ris_type}\n")
        output.write(f"TI  - {a.title}\n")

        for author in a.authors:
            output.write(f"AU  - {author}\n")

        if a.journal:
            output.write(f"JO  - {a.journal}\n")
        if a.year:
            month_str = f"/{a.month:02d}" if a.month else ""
            output.write(f"PY  - {a.year}{month_str}\n")
        if a.volume:
            output.write(f"VL  - {a.volume}\n")
        if a.issue:
            output.write(f"IS  - {a.issue}\n")
        if a.pages:
            parts = a.pages.split("-")
            output.write(f"SP  - {parts[0]}\n")
            if len(parts) > 1:
                output.write(f"EP  - {parts[1]}\n")
        if a.doi:
            output.write(f"DO  - {a.doi}\n")
        if a.pmid:
            output.write(f"AN  - PMID:{a.pmid}\n")
        if a.abstract:
            output.write(f"AB  - {a.abstract}\n")
        for kw in a.keywords:
            output.write(f"KW  - {kw}\n")
        if a.url:
            output.write(f"UR  - {a.url}\n")
        if a.issn:
            output.write(f"SN  - {a.issn}\n")
        if a.language:
            output.write(f"LA  - {a.language}\n")

        output.write("ER  - \n\n")

    return output.getvalue().encode("utf-8")


# ─── BibTeX ───────────────────────────────────────────────────────────────────

def _make_bibtex_key(article: Article) -> str:
    """Genera clave BibTeX limpia y única."""
    first_author = article.authors[0].split()[-1] if article.authors else "Unknown"
    first_author = re.sub(r"[^\w]", "", first_author)
    year = str(article.year) if article.year else "XXXX"
    title_word = re.sub(r"[^\w]", "", (article.title.split()[0] if article.title else "Untitled"))
    return f"{first_author}{year}{title_word}"


def to_bibtex_bytes(articles: List[Article]) -> bytes:
    """Exporta a formato BibTeX (compatible con LaTeX, Overleaf)."""
    if not articles:
        return b""

    output = io.StringIO()
    for a in articles:
        key = _make_bibtex_key(a)
        bib_type = "article"
        if a.article_type == "book_chapter":
            bib_type = "incollection"
        elif a.article_type == "dissertation":
            bib_type = "phdthesis"
        elif a.article_type == "preprint":
            bib_type = "misc"

        output.write(f"@{bib_type}{{{key},\n")
        output.write(f"  title = {{{a.title}}},\n")

        if a.authors:
            output.write(f"  author = {{{' and '.join(a.authors)}}},\n")
        if a.journal:
            output.write(f"  journal = {{{a.journal}}},\n")
        if a.year:
            output.write(f"  year = {{{a.year}}},\n")
        if a.month:
            output.write(f"  month = {{{a.month}}},\n")
        if a.volume:
            output.write(f"  volume = {{{a.volume}}},\n")
        if a.issue:
            output.write(f"  number = {{{a.issue}}},\n")
        if a.pages:
            output.write(f"  pages = {{{a.pages}}},\n")
        if a.doi:
            output.write(f"  doi = {{{a.doi}}},\n")
        if a.url:
            output.write(f"  url = {{{a.url}}},\n")
        if a.abstract:
            # BibTeX no tolera llaves sin escapar en el abstract
            abstract_clean = a.abstract.replace("{", "").replace("}", "")
            output.write(f"  abstract = {{{abstract_clean}}},\n")
        if a.issn:
            output.write(f"  issn = {{{a.issn}}},\n")
        if a.pmid:
            output.write(f"  note = {{PMID: {a.pmid}}},\n")

        output.write("}\n\n")

    return output.getvalue().encode("utf-8")


# ─── NotebookLM ───────────────────────────────────────────────────────────────

def generate_notebooklm_zip(
    articles: List[Article],
    collection_name: str = "collection",
) -> bytes:
    """
    Genera un ZIP con estructura lista para NotebookLM:
      {collection_name}/
        README.md
        resumen_master.csv
        metadata.json
        fichas/{safe_filename}.md   (una por artículo)
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{collection_name}/README.md",
                    _generate_readme(articles, collection_name))
        zf.writestr(f"{collection_name}/resumen_master.csv",
                    to_csv_bytes(articles))
        zf.writestr(f"{collection_name}/metadata.json",
                    to_json_bytes(articles))
        for article in articles:
            filename = _safe_filename(article)
            zf.writestr(f"{collection_name}/fichas/{filename}.md",
                        _generate_ficha_md(article))

    buf.seek(0)
    return buf.read()


def _safe_filename(article: Article, max_len: int = 60) -> str:
    """Genera nombre de archivo limpio, estable y apto para sistemas de archivos."""
    prefix = (
        article.pmid
        or (article.doi.replace("/", "_").replace(":", "_") if article.doi else None)
        or "art"
    )
    title_part = re.sub(r"[^\w\s-]", "", article.title or "")
    title_part = re.sub(r"\s+", "_", title_part)[:max_len]
    return f"{prefix}_{title_part}"


def _generate_readme(articles: List[Article], collection_name: str) -> str:
    sources  = sorted(set(a.source_database for a in articles))
    oa_count = sum(1 for a in articles if a.open_access_status == "open")
    types: dict = {}
    for a in articles:
        t = a.article_type or "unknown"
        types[t] = types.get(t, 0) + 1

    lines = [
        f"# Colección: {collection_name}",
        f"\n**Fecha de exportación:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total de artículos:** {len(articles)}",
        f"**Artículos de acceso abierto:** {oa_count}",
        f"**Fuentes:** {', '.join(sources)}",
        "\n## Distribución por tipo de estudio\n",
    ]
    for t, cnt in sorted(types.items(), key=lambda x: -x[1]):
        lines.append(f"- {t}: {cnt}")

    lines += [
        "\n## Archivos incluidos\n",
        "- `README.md` — Este archivo",
        "- `resumen_master.csv` — Tabla con todos los artículos (abrir en Excel o Google Sheets)",
        "- `metadata.json` — Metadatos completos en JSON",
        "- `fichas/` — Ficha individual en Markdown por artículo",
        "\n## Cómo usar en NotebookLM\n",
        "1. Sube `resumen_master.csv` como fuente de datos tabular",
        "2. Sube los archivos `.md` de `fichas/` que sean relevantes para tu pregunta",
        "3. Usa `metadata.json` para consultas estructuradas",
        "\n---\n*Generado por MedLib v0.2.0*",
    ]
    return "\n".join(lines)


def _generate_ficha_md(article: Article) -> str:
    """
    Genera ficha estructurada en Markdown para un artículo.
    Incluye referencia Vancouver, metadatos, abstract y ficha clínica PICO.
    """
    lines = [
        f"# {article.title}",
        "",
        "## Referencia",
        f"**Vancouver:** {article.to_vancouver()}",
        "",
    ]

    if article.doi:
        lines.append(f"**DOI:** [{article.doi}](https://doi.org/{article.doi})")
    if article.pmid:
        lines.append(
            f"**PMID:** [{article.pmid}](https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/)"
        )
    if article.pmcid:
        lines.append(f"**PMCID:** {article.pmcid}")

    lines += [
        "",
        "## Metadatos",
        f"- **Fuente:** {article.source_database}",
        f"- **Año:** {article.year or 'N/A'}",
        f"- **Tipo de estudio:** {article.article_type or 'N/A'}",
        f"- **Idioma:** {article.language or 'N/A'}",
        f"- **Acceso:** {article.access_type or 'N/A'}",
        f"- **Score de calidad:** {article.quality_score or 'N/A'}/100",
        "",
        "## Abstract",
        article.abstract or "*No disponible*",
        "",
    ]

    if article.keywords or article.mesh_terms:
        lines.append("## Palabras clave / MeSH")
        if article.keywords:
            lines.append(f"**Keywords:** {', '.join(article.keywords)}")
        if article.mesh_terms:
            lines.append(f"**MeSH:** {', '.join(article.mesh_terms)}")
        lines.append("")

    has_clinical = any([
        article.clinical_question, article.study_design, article.population,
        article.intervention, article.main_finding,
    ])
    if has_clinical:
        lines += [
            "## Ficha Clínica",
            f"**Pregunta clínica:** {article.clinical_question or 'Pendiente'}",
            f"**Diseño:** {article.study_design or 'Pendiente'}",
            f"**Población:** {article.population or 'Pendiente'}",
            f"**Intervención/Exposición:** {article.intervention or 'Pendiente'}",
            f"**Comparador:** {article.comparator or 'N/A'}",
            f"**Outcomes:** {article.outcomes or 'Pendiente'}",
            f"**Hallazgo principal:** {article.main_finding or 'Pendiente'}",
            f"**Limitaciones:** {article.limitations or 'Pendiente'}",
            f"**Utilidad clínica:** {article.clinical_utility or 'Pendiente'}",
            f"**Nivel de evidencia:** {article.evidence_level or 'Pendiente'}",
            "",
        ]

    if article.user_notes:
        lines += ["## Notas del Usuario", article.user_notes, ""]

    lines += [
        "---",
        f"*Recuperado: {article.date_retrieved.strftime('%Y-%m-%d') if article.date_retrieved else 'N/A'}*",
        f"*Colección: {article.collection_name}*",
    ]
    return "\n".join(lines)
