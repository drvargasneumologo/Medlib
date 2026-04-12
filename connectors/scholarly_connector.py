"""
Conector Google Scholar vía la librería `scholarly`.
https://scholarly.readthedocs.io/

ADVERTENCIAS CRÍTICAS — LEER ANTES DE USAR
-------------------------------------------
1. Google Scholar NO tiene API oficial. Este conector usa ingeniería inversa
   del HTML público de Scholar, lo cual puede violar los Términos de Servicio
   de Google si se hace de forma masiva o automatizada.

2. Google Scholar bloquea IPs que hacen demasiadas peticiones (CAPTCHA,
   HTTP 429, bloqueos temporales). El módulo está desactivado por defecto.

3. scholarly puede resolver CAPTCHAs vía FreeProxy o Tor, pero esto NO está
   implementado aquí por razones éticas y de estabilidad.

4. Uso recomendado: búsquedas manuales, pocas peticiones, esperas largas.
   NO usar en loops automatizados ni en producción.

5. scholarly no garantiza completitud de resultados. Scholar oculta >100 páginas
   de resultados, limita acceso anónimo y cambia su HTML sin aviso.

USO LEGÍTIMO
------------
- Investigación personal, no comercial.
- Complemento para encontrar citas/citaciones no indexadas en PubMed.
- Máximo 10-20 resultados por sesión para evitar bloqueos.

DEPENDENCIA EXTRA REQUERIDA
----------------------------
    pip install scholarly

No está en requirements.txt por defecto. Se instala solo si el usuario
activa explícitamente Google Scholar en Settings.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from models.article import Article

logger = logging.getLogger(__name__)

# Advertencia visible en la UI cada vez que se usa este conector
SCHOLAR_WARNING = (
    "⚠️ Google Scholar no tiene API oficial. "
    "El scraping puede violar sus Términos de Servicio y provocar bloqueos de IP. "
    "Usa con moderación: máx. 20 resultados, solo uso personal."
)


def is_scholarly_available() -> bool:
    """Verifica si la librería scholarly está instalada."""
    try:
        import scholarly  # noqa: F401
        return True
    except ImportError:
        return False


def search_google_scholar(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> List[Article]:
    """
    Busca en Google Scholar vía la librería scholarly.

    LIMITACIONES CONOCIDAS:
    - Sin PMID/PMCID (Scholar no los provee).
    - Sin abstract completo (Scholar trunca a ~200 chars).
    - Los metadatos (año, revista, páginas) son incompletos o aproximados.
    - Puede fallar silenciosamente si Scholar devuelve CAPTCHA.
    - La calidad de los datos es inferior a PubMed/Europe PMC.

    Args:
        query:       Términos de búsqueda. Soporta operadores Scholar.
        max_results: Máximo de resultados (recomendado ≤ 20).
        year_from:   Año de inicio (filtro Scholar).
        year_to:     Año de fin (filtro Scholar).

    Returns:
        Lista de Article con metadatos parciales.
        Retorna [] si scholarly no está instalado o hay error.
    """
    if not is_scholarly_available():
        logger.warning(
            "scholarly no está instalado. Ejecuta: pip install scholarly"
        )
        return []

    # Cap estricto para evitar bloqueos
    max_results = min(max_results, 20)

    try:
        from scholarly import scholarly as sch
    except Exception as exc:
        logger.error("Error importando scholarly: %s", exc)
        return []

    logger.warning("Google Scholar: %s", SCHOLAR_WARNING)
    logger.info("Scholar query: '%s' max=%d", query, max_results)

    articles: List[Article] = []

    try:
        search_kwargs: dict = {"query": query}
        if year_from:
            search_kwargs["patents"] = False
            search_kwargs["year_low"] = year_from
        if year_to:
            search_kwargs["year_high"] = year_to

        search_gen = sch.search_pubs(**search_kwargs)

        for i, pub in enumerate(search_gen):
            if i >= max_results:
                break
            try:
                a = _parse_scholar_pub(pub, query)
                if a:
                    articles.append(a)
                # Pausa entre peticiones para no saturar Scholar
                time.sleep(2.0)
            except Exception as exc:
                logger.warning("Error parseando resultado Scholar %d: %s", i, exc)
                continue

    except Exception as exc:
        error_msg = str(exc)
        if "CAPTCHA" in error_msg or "429" in error_msg or "blocked" in error_msg.lower():
            logger.error(
                "Google Scholar bloqueó la petición (CAPTCHA/rate limit). "
                "Espera varios minutos antes de volver a intentarlo."
            )
        else:
            logger.error("Error en búsqueda Scholar: %s", exc)

    logger.info("Google Scholar: %d artículos recuperados", len(articles))
    return articles


def _parse_scholar_pub(pub: dict, query_origin: str) -> Optional[Article]:
    """
    Parsea un resultado de scholarly a Article.
    Los metadatos de Scholar son más incompletos que los de PubMed.
    """
    bib = pub.get("bib") or {}

    title = (bib.get("title") or "").strip()
    if not title:
        return None

    abstract = (bib.get("abstract") or "").strip() or None
    # Scholar trunca abstracts — señalar esto
    if abstract and len(abstract) < 200 and not abstract.endswith("."):
        abstract = abstract + " [Abstract truncado por Google Scholar]"

    # Autores: Scholar devuelve string "Apellido A, Apellido B"
    authors_raw = bib.get("author") or ""
    if isinstance(authors_raw, list):
        authors = [a.strip() for a in authors_raw if a.strip()]
    elif isinstance(authors_raw, str):
        authors = [a.strip() for a in authors_raw.split(" and ") if a.strip()]
    else:
        authors = []

    journal = (bib.get("venue") or bib.get("journal") or "").strip() or None
    year_raw = bib.get("pub_year") or bib.get("year")
    year = None
    if year_raw:
        try:
            year = int(str(year_raw))
        except ValueError:
            pass

    pages = (bib.get("pages") or "").strip() or None
    volume = (bib.get("volume") or "").strip() or None

    # DOI: Scholar a veces lo incluye en el URL o en eprint_url
    doi = None
    eprint_url = pub.get("eprint_url") or ""
    pub_url = pub.get("pub_url") or ""
    for url_candidate in [eprint_url, pub_url]:
        if "doi.org/" in url_candidate:
            doi_part = url_candidate.split("doi.org/")[-1].strip()
            if doi_part:
                doi = doi_part
                break

    # Citation count
    citation_count = pub.get("num_citations")

    # URL de Scholar (no es el artículo original)
    scholar_url = pub.get("pub_url") or pub.get("eprint_url") or None

    return Article(
        source_database="google_scholar",
        source_record_id=str(pub.get("author_pub_id") or title[:30]),
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        journal=journal,
        year=year,
        volume=volume,
        pages=pages,
        citation_count=int(citation_count) if citation_count else None,
        url=scholar_url,
        landing_page_url=scholar_url,
        open_access_status="unknown",
        access_type="unknown",
        search_query_origin=query_origin,
        flag_no_abstract=not bool(abstract),
        flag_incomplete_metadata=True,  # Scholar siempre tiene metadatos incompletos
        flag_parsing_error=False,
    )
