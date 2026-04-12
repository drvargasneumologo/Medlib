"""
Conector Crossref REST API.
https://api.crossref.org/

API pública sin clave. Polite Pool con email en User-Agent mejora rate limits.

LIMITACIONES CONOCIDAS
----------------------
- No provee OA status directamente (usar Unpaywall para eso).
- Los abstracts están en formato JATS XML; se limpian con regex pero pueden
  quedar entidades HTML sin resolver si son inusuales.
- Cobertura no-biomédica alta; filtrar por tipo journal-article cuando sea posible.
- Validación en vivo: pendiente. Solo se validó el parsing contra datos de muestra.
"""
from __future__ import annotations

import html
import logging
import os
import re
import time
from typing import List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from models.article import Article

logger = logging.getLogger(__name__)

CROSSREF_BASE = "https://api.crossref.org"
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "user@example.com")
APP_NAME = os.getenv("USER_AGENT_APP_NAME", "MedLib")

_HEADERS = {
    "User-Agent": f"{APP_NAME}/0.2 (mailto:{CONTACT_EMAIL})",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _get(url: str, params: dict) -> requests.Response:
    resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(0.1)
    return resp


def _clean_jats_abstract(raw: Optional[str]) -> Optional[str]:
    """
    Limpia un abstract en formato JATS XML.
    1. Elimina tags XML/HTML.
    2. Resuelve entidades HTML (e.g. &amp; → &).
    3. Colapsa espacios múltiples.
    Retorna None si el resultado queda vacío.
    """
    if not raw:
        return None
    # Eliminar tags XML/HTML
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    # Resolver entidades HTML estándar
    cleaned = html.unescape(cleaned)
    # Colapsar espacios
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


def search_crossref(
    query: str,
    max_results: int = 50,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    filter_type: Optional[str] = "journal-article",
) -> List[Article]:
    """
    Busca trabajos en Crossref.

    Args:
        query:       Términos de búsqueda libres.
        max_results: Máximo de resultados.
        year_from:   Año mínimo de publicación.
        year_to:     Año máximo.
        filter_type: Tipo de documento Crossref (default: journal-article).
    """
    articles: List[Article] = []
    rows_per_page = min(max_results, 100)
    offset = 0
    total_fetched = 0

    filters: List[str] = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if year_to:
        filters.append(f"until-pub-date:{year_to}")
    if filter_type:
        filters.append(f"type:{filter_type}")

    while total_fetched < max_results:
        params: dict = {
            "query":  query,
            "rows":   min(rows_per_page, max_results - total_fetched),
            "offset": offset,
            "select": (
                "DOI,title,author,container-title,published,volume,issue,"
                "page,abstract,ISSN,language,type,is-referenced-by-count,"
                "URL,link,subject"
            ),
        }
        if filters:
            params["filter"] = ",".join(filters)

        try:
            resp = _get(f"{CROSSREF_BASE}/works", params)
            data = resp.json()
        except Exception as exc:
            logger.error("Error Crossref search: %s", exc)
            break

        items = data.get("message", {}).get("items", [])
        if not items:
            break

        for item in items:
            try:
                a = _parse_crossref_item(item, query)
                if a:
                    articles.append(a)
            except Exception as exc:
                logger.warning("Error parseando Crossref item: %s", exc)

        total_fetched += len(items)
        offset += len(items)

        total_results = data.get("message", {}).get("total-results", 0)
        if total_fetched >= total_results:
            break

    logger.info("Crossref: %d artículos recuperados", len(articles))
    return articles


def lookup_doi(doi: str) -> Optional[Article]:
    """Recupera metadatos para un DOI específico vía Crossref."""
    try:
        resp = _get(f"{CROSSREF_BASE}/works/{doi}", {})
        data = resp.json()
        item = data.get("message", {})
        return _parse_crossref_item(item, f"doi:{doi}")
    except Exception as exc:
        logger.error("Error Crossref DOI lookup %s: %s", doi, exc)
        return None


def _parse_crossref_item(item: dict, query_origin: str) -> Optional[Article]:
    doi = item.get("DOI") or None
    if not doi:
        return None

    titles = item.get("title") or []
    if not isinstance(titles, list):
        titles = [titles]
    title = titles[0].strip() if titles else ""
    if not title:
        return None

    # Autores
    authors: List[str] = []
    for auth in item.get("author") or []:
        if not isinstance(auth, dict):
            continue
        given = (auth.get("given") or "").strip()
        family = (auth.get("family") or "").strip()
        name = auth.get("name", "").strip()
        if family:
            authors.append(f"{family} {given[0]}" if given else family)
        elif name:
            authors.append(name)

    # Revista
    container = item.get("container-title") or []
    if not isinstance(container, list):
        container = [container]
    journal = container[0].strip() if container else None

    # Fecha de publicación
    year, month = None, None
    for date_key in ("published", "published-print", "published-online"):
        pub = item.get(date_key)
        if pub:
            date_parts = pub.get("date-parts", [[]])[0]
            if date_parts:
                try:
                    year = int(date_parts[0]) if date_parts[0] else None
                    month = int(date_parts[1]) if len(date_parts) > 1 and date_parts[1] else None
                except (ValueError, TypeError):
                    pass
            if year:
                break

    volume   = item.get("volume") or None
    issue    = item.get("issue") or None
    pages    = item.get("page") or None
    language = item.get("language") or None
    article_type = _map_crossref_type(item.get("type") or "")
    citation_count = item.get("is-referenced-by-count")

    issn_list = item.get("ISSN") or []
    issn  = issn_list[0] if issn_list else None
    eissn = issn_list[1] if len(issn_list) > 1 else None

    # Abstract: puede venir en JATS XML
    abstract = _clean_jats_abstract(item.get("abstract"))

    url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)

    # PDF link si existe
    pdf_url = None
    for link in item.get("link") or []:
        if isinstance(link, dict) and link.get("content-type") == "application/pdf":
            pdf_url = link.get("URL")
            break

    subjects = item.get("subject") or []

    return Article(
        source_database="crossref",
        source_record_id=doi,
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        keywords=[s for s in subjects if isinstance(s, str)],
        journal=journal,
        year=year,
        month=month,
        volume=volume,
        issue=issue,
        pages=pages,
        language=language,
        article_type=article_type,
        issn=issn,
        eissn=eissn,
        url=url,
        landing_page_url=url,
        pdf_url=pdf_url,
        citation_count=int(citation_count) if citation_count is not None else None,
        access_type="unknown",
        open_access_status="unknown",
        search_query_origin=query_origin,
        flag_no_abstract=not bool(abstract),
        flag_incomplete_metadata=not bool(year or journal),
    )


def _map_crossref_type(cr_type: str) -> Optional[str]:
    _map = {
        "journal-article":     "journal_article",
        "book-chapter":        "book_chapter",
        "proceedings-article": "conference",
        "dissertation":        "dissertation",
        "preprint":            "preprint",
        "review-article":      "review",
        "report":              "report",
    }
    return _map.get(cr_type)
