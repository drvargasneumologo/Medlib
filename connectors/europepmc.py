"""
Conector Europe PMC REST API.
https://europepmc.org/RestfulWebService

API pública sin autenticación requerida.

LIMITACIONES CONOCIDAS
----------------------
- Cuando una respuesta contiene un solo autor, la API puede devolver un dict
  en lugar de una lista para author_list. Se maneja con isinstance().
- Los abstracts pueden incluir markup XML (JATS). Se limpian con regex básico.
- Validación en vivo: pendiente. Solo se validó el parsing contra datos de muestra.
- El campo 'affiliationList' a veces es una lista de strings, a veces de dicts.
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from models.article import Article

logger = logging.getLogger(__name__)

EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
TOOL_NAME = os.getenv("USER_AGENT_APP_NAME", "MedLib")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "user@example.com")

_HEADERS = {
    "User-Agent": f"{TOOL_NAME}/0.2 (mailto:{CONTACT_EMAIL})",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _get(url: str, params: dict) -> requests.Response:
    resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(0.2)
    return resp


def search_europepmc(
    query: str,
    max_results: int = 50,
    date_from: Optional[int] = None,
    date_to: Optional[int] = None,
    open_access_only: bool = False,
    has_fulltext: bool = False,
    source: str = "MED",
) -> List[Article]:
    """
    Busca en Europe PMC.

    Args:
        query:            Términos. Soporta AND/OR, TITLE:, ABSTRACT:, AUTH:.
        max_results:      Máximo de resultados.
        date_from:        Año de inicio (entero).
        date_to:          Año de fin (entero).
        open_access_only: Solo artículos OA.
        has_fulltext:     Solo con texto completo disponible.
        source:           MED (MEDLINE), PMC, PPR (preprints), ALL.
    """
    full_query = _build_epmc_query(
        query, date_from, date_to, open_access_only, has_fulltext, source
    )
    logger.info("Europe PMC query: %s", full_query)

    articles: List[Article] = []
    page_size  = min(max_results, 1000)
    cursor_mark = "*"
    total_fetched = 0

    while total_fetched < max_results:
        params = {
            "query":       full_query,
            "format":      "json",
            "pageSize":    min(page_size, max_results - total_fetched),
            "resultType":  "core",
            "cursorMark":  cursor_mark,
        }

        try:
            resp = _get(f"{EPMC_BASE}/search", params)
            data = resp.json()
        except Exception as exc:
            logger.error("Error en Europe PMC search: %s", exc)
            break

        result_list = data.get("resultList", {}).get("result", [])
        if not result_list:
            break

        for item in result_list:
            try:
                a = _parse_epmc_result(item, full_query)
                if a:
                    articles.append(a)
            except Exception as exc:
                logger.warning("Error parseando resultado EPMC: %s", exc)

        total_fetched += len(result_list)

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor_mark:
            break
        cursor_mark = next_cursor

        hit_count = int(data.get("hitCount", 0))
        logger.debug("EPMC: recuperados %d / %d", total_fetched, hit_count)

    logger.info("Europe PMC: %d artículos recuperados", len(articles))
    return articles


def _build_epmc_query(
    base_query: str,
    date_from: Optional[int],
    date_to: Optional[int],
    open_access_only: bool,
    has_fulltext: bool,
    source: str,
) -> str:
    parts = [f"({base_query})"]
    if date_from:
        dt = date_to or 3000
        parts.append(f"FIRST_PDATE:[{date_from}-01-01 TO {dt}-12-31]")
    if open_access_only:
        parts.append("OPEN_ACCESS:y")
    if has_fulltext:
        parts.append("HAS_FULLTEXT:y")
    if source and source != "ALL":
        parts.append(f"SRC:{source}")
    return " AND ".join(parts)


def _extract_authors(item: dict) -> List[str]:
    """
    Extrae lista de autores de forma robusta.
    La API puede devolver list, dict, o None en 'authorList.author'.
    """
    author_list = (item.get("authorList") or {}).get("author")
    if not author_list:
        return []

    # Si es un solo autor, la API devuelve dict en lugar de list
    if isinstance(author_list, dict):
        author_list = [author_list]
    elif not isinstance(author_list, list):
        return []

    authors = []
    for auth in author_list:
        if not isinstance(auth, dict):
            continue
        full = (auth.get("fullName") or "").strip()
        last = (auth.get("lastName") or "").strip()
        if full:
            authors.append(full)
        elif last:
            authors.append(last)
    return authors


def _extract_affiliation(item: dict) -> Optional[str]:
    """Extrae primera afiliación disponible de forma robusta."""
    aff_list = (item.get("affiliationList") or {}).get("affiliation")
    if not aff_list:
        return None
    if isinstance(aff_list, str):
        return aff_list.strip() or None
    if isinstance(aff_list, list) and aff_list:
        first = aff_list[0]
        if isinstance(first, str):
            return first.strip() or None
        if isinstance(first, dict):
            return (first.get("affiliation") or "").strip() or None
    return None


def _parse_epmc_result(item: dict, query_origin: str) -> Optional[Article]:
    pmid      = item.get("pmid") or None
    pmcid     = item.get("pmcid") or None
    doi       = item.get("doi") or None
    source_db = item.get("source") or "MED"
    source_id = str(item.get("id") or "")

    title = (item.get("title") or "").strip()
    if not title:
        return None

    abstract = (item.get("abstractText") or "").strip() or None

    authors    = _extract_authors(item)
    affiliation = _extract_affiliation(item)

    journal = item.get("journalTitle") or (
        (item.get("journalInfo") or {}).get("journal") or {}
    ).get("title")

    year_str = item.get("pubYear")
    year = int(year_str) if year_str and str(year_str).isdigit() else None

    journal_info = item.get("journalInfo") or {}
    volume = journal_info.get("volume") or None
    issue  = journal_info.get("issue") or None
    issn   = item.get("issn") or None
    pages  = item.get("pageInfo") or None
    language = item.get("language") or None

    pub_types = (item.get("pubTypeList") or {}).get("pubType") or []
    if isinstance(pub_types, str):
        pub_types = [pub_types]
    article_type = _map_epmc_type(pub_types)

    keywords: List[str] = []
    kw_list = (item.get("keywordList") or {}).get("keyword") or []
    if isinstance(kw_list, list):
        keywords = [k for k in kw_list if isinstance(k, str)]
    elif isinstance(kw_list, str):
        keywords = [kw_list]

    mesh_terms: List[str] = []
    for mh in (item.get("meshHeadingList") or {}).get("meshHeading") or []:
        if isinstance(mh, dict):
            desc = mh.get("descriptorName")
            if desc:
                mesh_terms.append(str(desc))

    is_oa = item.get("isOpenAccess") == "Y"
    has_ft = item.get("hasFullTextXML") == "Y" or item.get("hasFullTextPDF") == "Y"

    url = None
    if pmid:
        url = f"https://europepmc.org/article/MED/{pmid}"
    elif pmcid:
        url = f"https://europepmc.org/article/PMC/{pmcid.replace('PMC', '')}"
    elif source_id:
        url = f"https://europepmc.org/article/{source_db}/{source_id}"

    pdf_url = None
    if pmcid and has_ft:
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"

    cit = item.get("citedByCount")
    citation_count = int(cit) if cit is not None else None

    flag_preprint = source_db in ("PPR",) or "preprint" in " ".join(pub_types).lower()

    return Article(
        source_database=f"europepmc_{source_db.lower()}",
        source_record_id=source_id,
        pmid=str(pmid) if pmid else None,
        pmcid=str(pmcid) if pmcid else None,
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        keywords=keywords,
        mesh_terms=mesh_terms,
        journal=journal,
        year=year,
        volume=volume,
        issue=issue,
        issn=issn,
        pages=pages,
        language=language,
        article_type=article_type,
        affiliation=affiliation,
        open_access_status="open" if is_oa else "unknown",
        access_type="open_access" if is_oa else "unknown",
        url=url,
        landing_page_url=url,
        pdf_url=pdf_url,
        citation_count=citation_count,
        search_query_origin=query_origin,
        flag_preprint=flag_preprint,
        flag_no_abstract=not bool(abstract),
        flag_incomplete_metadata=not bool(year or journal),
    )


def _map_epmc_type(pub_types: List[str]) -> Optional[str]:
    _map = {
        "meta-analysis":            "meta_analysis",
        "systematic review":        "systematic_review",
        "randomized controlled trial": "rct",
        "clinical trial":           "clinical_trial",
        "review":                   "review",
        "case report":              "case_report",
        "observational study":      "observational",
        "editorial":                "editorial",
        "letter":                   "letter",
        "preprint":                 "preprint",
        "guideline":                "guideline",
        "practice guideline":       "guideline",
    }
    for pt in pub_types:
        pt_lower = pt.lower()
        for key, val in _map.items():
            if key in pt_lower:
                return val
    return None
