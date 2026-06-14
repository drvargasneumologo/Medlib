"""
Conector PubMed / MEDLINE vía NCBI E-utilities.
API oficial: https://www.ncbi.nlm.nih.gov/books/NBK25501/
Sin clave API: máx 3 req/s. Con NCBI_API_KEY: 10 req/s.
"""
from __future__ import annotations
import logging
import os
import time
import xml.etree.ElementTree as ET
from typing import List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from models.article import Article

logger = logging.getLogger(__name__)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = os.getenv("USER_AGENT_APP_NAME", "MedLib")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "user@example.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

_ARTICLE_TYPE_MAP = {
    "Clinical Trial": "clinical_trial",
    "Randomized Controlled Trial": "rct",
    "Meta-Analysis": "meta_analysis",
    "Systematic Review": "systematic_review",
    "Review": "review",
    "Observational Study": "observational",
    "Case Reports": "case_report",
    "Editorial": "editorial",
    "Letter": "letter",
    "Comment": "comment",
    "Practice Guideline": "guideline",
    "Guideline": "guideline",
    "Preprint": "preprint",
}


def _base_params() -> dict:
    params = {"tool": TOOL_NAME, "email": CONTACT_EMAIL}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _get(url: str, params: dict) -> requests.Response:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    time.sleep(0.34 if not NCBI_API_KEY else 0.11)
    return resp


def search_pubmed(
    query: str,
    max_results: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    article_types: Optional[List[str]] = None,
    language: Optional[str] = None,
    humans_only: bool = False,
    has_abstract: bool = False,
    has_fulltext: bool = False,
) -> List[Article]:
    """
    Busca en PubMed y retorna lista de Article.

    Args:
        query: Query PubMed (soporta MeSH, booleanos, campos [ti], [au], etc.)
        max_results: Máximo de resultados a recuperar
        date_from: YYYY/MM/DD
        date_to: YYYY/MM/DD
        article_types: Lista de tipos, ej. ["Clinical Trial", "Meta-Analysis"]
        language: "english", "spanish", etc.
        humans_only: Añade filtro Humans
        has_abstract: Solo artículos con abstract
        has_fulltext: Solo artículos con texto completo en PMC
    """
    full_query = _build_query(
        query, date_from, date_to, article_types, language, humans_only, has_abstract, has_fulltext
    )
    logger.info("PubMed query: %s", full_query)

    # ESearch para obtener IDs
    search_params = {
        **_base_params(),
        "db": "pubmed",
        "term": full_query,
        "retmax": min(max_results, 10000),
        "retmode": "json",
        "usehistory": "y",
    }
    try:
        resp = _get(f"{EUTILS_BASE}/esearch.fcgi", search_params)
        data = resp.json()
        result = data.get("esearchresult", {})
        ids = result.get("idlist", [])
        total = int(result.get("count", 0))
        webenv = result.get("webenv", "")
        query_key = result.get("querykey", "")
        logger.info("PubMed encontró %d resultados, recuperando %d", total, len(ids))
    except Exception as e:
        logger.error("Error en ESearch: %s", e)
        raise

    if not ids:
        return []

    # EFetch en lotes de 200
    articles = []
    batch_size = 200
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        fetch_params = {
            **_base_params(),
            "db": "pubmed",
            "id": ",".join(batch_ids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        try:
            resp = _get(f"{EUTILS_BASE}/efetch.fcgi", fetch_params)
            batch_articles = _parse_pubmed_xml(resp.text, full_query)
            articles.extend(batch_articles)
        except Exception as e:
            logger.error("Error en EFetch lote %d: %s", i // batch_size, e)

    return articles


def _build_query(
    base_query: str,
    date_from, date_to, article_types, language, humans_only, has_abstract, has_fulltext
) -> str:
    parts = [f"({base_query})"]

    if date_from or date_to:
        df = date_from or "1900/01/01"
        dt = date_to or "3000/12/31"
        parts.append(f'("{df}"[dp] : "{dt}"[dp])')

    if article_types:
        type_filters = " OR ".join(f'"{t}"[pt]' for t in article_types)
        parts.append(f"({type_filters})")

    if language:
        parts.append(f'"{language}"[lang]')

    if humans_only:
        parts.append('"Humans"[mh]')

    if has_abstract:
        parts.append('"hasabstract"[text]')

    if has_fulltext:
        parts.append('"loattrfree full text"[sb]')

    return " AND ".join(parts)


def _parse_pubmed_xml(xml_text: str, query_origin: str) -> List[Article]:
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error("Error parseando XML PubMed: %s", e)
        return []

    for article_node in root.findall(".//PubmedArticle"):
        try:
            a = _parse_single_article(article_node, query_origin)
            if a:
                articles.append(a)
        except Exception as e:
            logger.warning("Error parseando artículo individual: %s", e)

    return articles


def _parse_single_article(node: ET.Element, query_origin: str) -> Optional[Article]:
    medline = node.find("MedlineCitation")
    if medline is None:
        return None

    article_node = medline.find("Article")
    if article_node is None:
        return None

    # PMID
    pmid_node = medline.find("PMID")
    pmid = pmid_node.text.strip() if pmid_node is not None and pmid_node.text else None

    # PMCID y DOI desde PubmedData
    pmcid = None
    doi = None
    pubmed_data = node.find("PubmedData")
    if pubmed_data is not None:
        for id_node in pubmed_data.findall(".//ArticleId"):
            id_type = id_node.get("IdType", "")
            if id_type == "pmc" and id_node.text:
                pmcid = id_node.text.strip()
            elif id_type == "doi" and id_node.text:
                doi = id_node.text.strip()

    # Título
    title_node = article_node.find(".//ArticleTitle")
    title = _get_text(title_node)

    # Abstract
    abstract_parts = []
    for abs_text in article_node.findall(".//AbstractText"):
        label = abs_text.get("Label", "")
        text = _get_text(abs_text)
        if text:
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
    abstract = " ".join(abstract_parts) or None

    # Autores
    authors = []
    for author in article_node.findall(".//Author"):
        last = _get_text(author.find("LastName"))
        first = _get_text(author.find("ForeName"))
        initials = _get_text(author.find("Initials"))
        collective = _get_text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
        elif last:
            name = last
            if initials:
                name += f" {initials}"
            elif first:
                name += f" {first[0]}"
            authors.append(name)

    # Revista
    journal_node = article_node.find(".//Journal")
    journal = None
    issn = None
    if journal_node is not None:
        jt = journal_node.find("Title")
        journal = _get_text(jt)
        issn_node = journal_node.find("ISSN")
        issn = _get_text(issn_node)

    # Fecha
    year, month = None, None
    pub_date = article_node.find(".//PubDate")
    if pub_date is not None:
        year_node = pub_date.find("Year")
        month_node = pub_date.find("Month")
        medline_date = pub_date.find("MedlineDate")
        if year_node is not None and year_node.text:
            try:
                year = int(year_node.text)
            except ValueError:
                pass
        if month_node is not None and month_node.text:
            month_map = {
                "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
            }
            month = month_map.get(month_node.text, None)
        if not year and medline_date is not None and medline_date.text:
            try:
                year = int(medline_date.text[:4])
            except (ValueError, IndexError):
                pass

    # Volumen, issue, páginas
    volume = _get_text(article_node.find(".//Volume"))
    issue = _get_text(article_node.find(".//Issue"))
    pages = _get_text(article_node.find(".//MedlinePgn"))

    # Idioma
    lang_node = article_node.find("Language")
    language = _get_text(lang_node)

    # Tipos de artículo
    article_types = []
    for pt in article_node.findall(".//PublicationType"):
        if pt.text:
            article_types.append(pt.text.strip())

    article_type = None
    for pt in article_types:
        if pt in _ARTICLE_TYPE_MAP:
            article_type = _ARTICLE_TYPE_MAP[pt]
            break

    # Keywords
    keywords = []
    for kw in medline.findall(".//Keyword"):
        if kw.text:
            keywords.append(kw.text.strip())

    # MeSH terms
    mesh_terms = []
    for mh in medline.findall(".//MeshHeading"):
        desc = mh.find("DescriptorName")
        if desc is not None and desc.text:
            mesh_terms.append(desc.text.strip())

    # Afiliación
    aff_node = article_node.find(".//Affiliation")
    affiliation = _get_text(aff_node)

    # URLs
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
    landing_page_url = url
    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/" if pmcid else None

    # OA status
    open_access = "open" if pmcid else "unknown"
    access_type = "open_access" if pmcid else "unknown"

    # Flags
    flag_no_abstract = not bool(abstract)
    flag_preprint = "Preprint" in article_types
    flag_incomplete = not pmid or not title

    return Article(
        source_database="pubmed",
        source_record_id=pmid or "",
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        keywords=keywords,
        mesh_terms=mesh_terms,
        journal=journal,
        year=year,
        month=month,
        volume=volume,
        issue=issue,
        pages=pages,
        language=language,
        article_type=article_type,
        issn=issn,
        affiliation=affiliation,
        open_access_status=open_access,
        access_type=access_type,
        url=url,
        landing_page_url=landing_page_url,
        pdf_url=pdf_url,
        search_query_origin=query_origin,
        flag_no_abstract=flag_no_abstract,
        flag_preprint=flag_preprint,
        flag_incomplete_metadata=flag_incomplete,
    )


def _get_text(node) -> Optional[str]:
    if node is None:
        return None
    # Incluye text de sub-elementos (para ArticleTitle con tags)
    text = "".join(node.itertext()).strip()
    return text if text else None
