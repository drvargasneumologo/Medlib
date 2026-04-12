"""
Servicio orquestador de búsqueda.
Coordina múltiples conectores, deduplicación, scoring y almacenamiento.
"""
from __future__ import annotations
import logging
from datetime import UTC, datetime
from typing import List, Optional, Dict, Any

from models.article import Article, SearchLog
from services.dedup_service import deduplicate_articles
from services.scoring_service import score_batch
from storage.database import upsert_article, log_search

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


def run_search(
    query: str,
    sources: List[str],
    collection_name: str = "default",
    max_results: int = 50,
    # Filtros comunes
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    language: Optional[str] = None,
    article_types: Optional[List[str]] = None,
    open_access_only: bool = False,
    humans_only: bool = False,
    has_abstract: bool = False,
    has_fulltext: bool = False,
    # Control
    deduplicate: bool = True,
    score: bool = True,
    save_to_db: bool = True,
    scoring_weights: Optional[Dict] = None,
    current_year: int = 2024,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Ejecuta búsqueda en múltiples fuentes.

    Returns:
        {
            "articles": List[Article],
            "total_raw": int,
            "total_unique": int,
            "total_saved": int,
            "duplicates_found": int,
            "logs": List[SearchLog],
            "errors": List[str],
        }
    """
    all_articles: List[Article] = []
    logs: List[SearchLog] = []
    errors: List[str] = []
    total_steps = len(sources)

    for step, source in enumerate(sources):
        if progress_callback:
            progress_callback(step / total_steps, f"Buscando en {source}...")

        articles_from_source = []
        error_msg = None

        try:
            articles_from_source = _search_source(
                source=source,
                query=query,
                max_results=max_results,
                date_from=date_from,
                date_to=date_to,
                year_from=year_from,
                year_to=year_to,
                language=language,
                article_types=article_types,
                open_access_only=open_access_only,
                humans_only=humans_only,
                has_abstract=has_abstract,
                has_fulltext=has_fulltext,
            )
        except Exception as e:
            error_msg = f"{source}: {str(e)}"
            errors.append(error_msg)
            logger.error("Error buscando en %s: %s", source, e)

        # Asignar colección
        for a in articles_from_source:
            a.collection_name = collection_name

        all_articles.extend(articles_from_source)

        # Log de búsqueda
        log = SearchLog(
            timestamp=datetime.now(UTC),
            source=source,
            query=query,
            filters={
                "date_from": date_from,
                "date_to": date_to,
                "year_from": year_from,
                "year_to": year_to,
                "language": language,
                "article_types": article_types,
                "open_access_only": open_access_only,
                "humans_only": humans_only,
                "has_abstract": has_abstract,
                "has_fulltext": has_fulltext,
            },
            result_count=len(articles_from_source),
            collection_name=collection_name,
            app_version=APP_VERSION,
            error=error_msg,
        )
        logs.append(log)
        if save_to_db:
            log_search(log)

    total_raw = len(all_articles)

    if progress_callback:
        progress_callback(0.7, "Deduplicando...")

    # Deduplicación
    unique_articles = all_articles
    duplicate_pairs = []
    if deduplicate and all_articles:
        unique_articles, duplicate_pairs = deduplicate_articles(all_articles)

    if progress_callback:
        progress_callback(0.85, "Calculando scores...")

    # Scoring
    if score and unique_articles:
        score_batch(unique_articles, weights=scoring_weights, current_year=current_year)

    if progress_callback:
        progress_callback(0.9, "Guardando en biblioteca...")

    # Guardar
    total_saved = 0
    if save_to_db:
        for article in all_articles:  # Guardamos todos, incluyendo duplicados marcados
            try:
                upsert_article(article)
                total_saved += 1
            except Exception as e:
                logger.warning("Error guardando artículo '%s': %s", article.title[:40], e)

        # Actualizar logs con saved_count
        for log in logs:
            log.saved_count = total_saved

    if progress_callback:
        progress_callback(1.0, "Búsqueda completada.")

    return {
        "articles": unique_articles,
        "all_articles": all_articles,
        "total_raw": total_raw,
        "total_unique": len(unique_articles),
        "total_saved": total_saved,
        "duplicates_found": len(duplicate_pairs),
        "duplicate_pairs": duplicate_pairs,
        "logs": logs,
        "errors": errors,
    }


def _search_source(
    source: str,
    query: str,
    max_results: int,
    date_from, date_to, year_from, year_to,
    language, article_types, open_access_only,
    humans_only, has_abstract, has_fulltext,
) -> List[Article]:
    """Despacha la búsqueda al conector correcto."""

    if source == "pubmed":
        from connectors.pubmed import search_pubmed
        return search_pubmed(
            query=query,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
            article_types=article_types,
            language=language,
            humans_only=humans_only,
            has_abstract=has_abstract,
            has_fulltext=has_fulltext,
        )

    elif source == "europepmc":
        from connectors.europepmc import search_europepmc
        yf = year_from or (int(date_from[:4]) if date_from else None)
        yt = year_to or (int(date_to[:4]) if date_to else None)
        return search_europepmc(
            query=query,
            max_results=max_results,
            date_from=yf,
            date_to=yt,
            open_access_only=open_access_only,
            has_fulltext=has_fulltext,
        )

    elif source == "crossref":
        from connectors.crossref import search_crossref
        return search_crossref(
            query=query,
            max_results=max_results,
            year_from=year_from,
            year_to=year_to,
        )

    elif source == "openalex":
        from connectors.openalex import search_openalex
        return search_openalex(
            query=query,
            max_results=max_results,
            year_from=year_from,
            year_to=year_to,
            open_access_only=open_access_only,
        )


    elif source == "google_scholar":
        import os
        from connectors.scholarly_connector import search_google_scholar
        max_scholar = min(max_results, int(os.getenv("SCHOLAR_MAX_RESULTS", "10")))
        return search_google_scholar(
            query=query,
            max_results=max_scholar,
            year_from=year_from,
            year_to=year_to,
        )
    else:
        raise ValueError(f"Fuente no reconocida: {source}")


def import_pmids(
    pmids: List[str],
    collection_name: str = "default",
    save_to_db: bool = True,
) -> Dict[str, Any]:
    """Importa artículos a partir de una lista de PMIDs."""
    from connectors.pubmed import search_pubmed

    query = " OR ".join(f"{pmid}[uid]" for pmid in pmids)
    articles = search_pubmed(query=query, max_results=len(pmids))

    for a in articles:
        a.collection_name = collection_name

    score_batch(articles)

    saved = 0
    if save_to_db:
        for a in articles:
            try:
                upsert_article(a)
                saved += 1
            except Exception as e:
                logger.warning("Error guardando PMID: %s", e)

    return {"articles": articles, "saved": saved}
