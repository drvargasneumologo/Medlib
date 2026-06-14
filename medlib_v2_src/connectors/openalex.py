"""
Conector OpenAlex.
API abierta: https://docs.openalex.org/
Sin clave requerida. Polite Pool con email en User-Agent.
Excelente cobertura biomédica y datos de OA.
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

OA_BASE = "https://api.openalex.org"
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "user@example.com")
APP_NAME = os.getenv("USER_AGENT_APP_NAME", "MedLib")

_HEADERS = {
    "User-Agent": f"{APP_NAME}/0.1 (mailto:{CONTACT_EMAIL})",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _get(url: str, params: dict) -> requests.Response:
    resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(0.1)
    return resp


def search_openalex(
    query: str,
    max_results: int = 50,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    open_access_only: bool = False,
    concepts: Optional[List[str]] = None,
) -> List[Article]:
    """
    Busca en OpenAlex.
    Args:
        query: Términos de búsqueda
        max_results: Máximo de resultados
        year_from: Año mínimo
        year_to: Año máximo
        open_access_only: Solo OA
        concepts: Lista de conceptos OpenAlex (IDs o nombres)
    """
    articles = []
    page = 1
    per_page = min(max_results, 200)
    total_fetched = 0

    filter_parts = ["type:journal-article"]
    if year_from:
        filter_parts.append(f"publication_year:>{year_from - 1}")
    if year_to:
        filter_parts.append(f"publication_year:<{year_to + 1}")
    if open_access_only:
        filter_parts.append("is_oa:true")

    while total_fetched < max_results:
        params = {
            "search": query,
            "filter": ",".join(filter_parts),
            "per-page": min(per_page, max_results - total_fetched),
            "page": page,
            "select": (
                "id,doi,title,abstract_inverted_index,authorships,primary_location,"
                "publication_year,publication_date,biblio,open_access,best_oa_location,"
                "cited_by_count,concepts,keywords,language,type,ids"
            ),
            "mailto": CONTACT_EMAIL,
        }

        try:
            resp = _get(f"{OA_BASE}/works", params)
            data = resp.json()
        except Exception as e:
            logger.error("Error OpenAlex search: %s", e)
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            try:
                a = _parse_openalex_item(item, query)
                if a:
                    articles.append(a)
            except Exception as e:
                logger.warning("Error parseando OpenAlex item: %s", e)

        total_fetched += len(results)

        meta = data.get("meta", {})
        total_available = meta.get("count", 0)
        if total_fetched >= total_available:
            break
        page += 1

    logger.info("OpenAlex: %d artículos recuperados", len(articles))
    return articles


def _reconstruct_abstract(inverted_index: Optional[dict]) -> Optional[str]:
    """Reconstruye el abstract desde el índice invertido de OpenAlex."""
    if not inverted_index:
        return None
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


def _parse_openalex_item(item: dict, query_origin: str) -> Optional[Article]:
    doi_raw = item.get("doi")
    doi = doi_raw.replace("https://doi.org/", "").strip() if doi_raw else None

    title = item.get("title", "")
    if not title:
        return None

    # IDs externos
    ext_ids = item.get("ids", {})
    pmid = ext_ids.get("pmid", "").replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip() or None
    pmcid = ext_ids.get("pmcid", "").replace("https://www.ncbi.nlm.nih.gov/pmc/articles/", "").strip() or None

    # Abstract
    abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))

    # Autores
    authors = []
    for authorship in item.get("authorships", []):
        author = authorship.get("author", {})
        display_name = author.get("display_name", "")
        if display_name:
            authors.append(display_name)

    # Afiliación (primera del primer autor)
    affiliation = None
    authorships = item.get("authorships", [])
    if authorships:
        insts = authorships[0].get("institutions", [])
        if insts:
            affiliation = insts[0].get("display_name")

    # Revista
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    journal = source.get("display_name")
    issn_list = source.get("issn", []) or []
    issn = issn_list[0] if issn_list else None

    # Fecha
    year = item.get("publication_year")
    pub_date = item.get("publication_date", "")
    month = None
    if pub_date and len(pub_date) >= 7:
        try:
            month = int(pub_date[5:7])
        except ValueError:
            pass

    # Biblio
    biblio = item.get("biblio", {})
    volume = biblio.get("volume")
    issue = biblio.get("issue")
    first_page = biblio.get("first_page")
    last_page = biblio.get("last_page")
    pages = f"{first_page}-{last_page}" if first_page and last_page else first_page

    language = item.get("language")

    # OA
    oa = item.get("open_access", {})
    is_oa = oa.get("is_oa", False)
    oa_url = oa.get("oa_url")

    best_oa = item.get("best_oa_location") or {}
    pdf_url = best_oa.get("pdf_url") or (oa_url if oa_url and oa_url.endswith(".pdf") else None)
    landing_page_url = best_oa.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else None)

    open_access_status = "open" if is_oa else "unknown"
    access_type = "open_access" if is_oa else "unknown"

    # Conceptos como keywords
    concepts = item.get("concepts", []) or []
    keywords = [c.get("display_name", "") for c in concepts if c.get("score", 0) > 0.3]
    oa_kw = item.get("keywords", []) or []
    if isinstance(oa_kw, list):
        for kw in oa_kw:
            if isinstance(kw, dict):
                kw_name = kw.get("keyword") or kw.get("display_name", "")
                if kw_name:
                    keywords.append(kw_name)

    citation_count = item.get("cited_by_count")
    url = f"https://doi.org/{doi}" if doi else item.get("id")

    return Article(
        source_database="openalex",
        source_record_id=item.get("id", "").replace("https://openalex.org/", ""),
        doi=doi,
        pmid=pmid,
        pmcid=pmcid,
        title=title,
        abstract=abstract,
        authors=authors,
        keywords=keywords,
        journal=journal,
        year=year,
        month=month,
        volume=volume,
        issue=issue,
        issn=issn,
        pages=pages,
        language=language,
        affiliation=affiliation,
        open_access_status=open_access_status,
        access_type=access_type,
        url=url,
        landing_page_url=landing_page_url,
        pdf_url=pdf_url,
        citation_count=citation_count,
        search_query_origin=query_origin,
        flag_no_abstract=not bool(abstract),
        flag_incomplete_metadata=not bool(year or journal),
    )
