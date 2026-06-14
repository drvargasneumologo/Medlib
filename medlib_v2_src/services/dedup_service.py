"""
Servicio de deduplicación.
Estrategia en capas: DOI → PMID → PMCID → fingerprint → título fuzzy.
Mantiene trazabilidad completa de fuentes de origen.

NOTAS DE DISEÑO
---------------
- La mutación in-place de los objetos Article es intencional. Pydantic v2
  permite mutación por defecto (sin frozen=True). Los tests verifican este
  comportamiento explícitamente.
- source_database se almacena como lista de fuentes separadas por "+" cuando
  un artículo se detecta en múltiples fuentes. El scoring usa _is_biomedical()
  para manejar este caso correctamente (split y check por elemento).
- Los conflictos de merge se registran en el log pero no interrumpen el flujo.

VALIDACIÓN
----------
- Lógica de deduplicación: validada mediante tests unitarios offline (sin red).
- Comportamiento con respuestas reales de API: pendiente validación en vivo.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from rapidfuzz import fuzz

from models.article import Article

logger = logging.getLogger(__name__)

FUZZY_TITLE_THRESHOLD = 92  # Score mínimo para considerar duplicados por título


def is_biomedical_source(source_database: str) -> bool:
    """
    Verifica si la fuente es biomédica.
    Maneja el caso de source_database compuesto ("pubmed+crossref")
    generado por _merge_metadata.
    """
    _BIOMEDICAL_SOURCES: Set[str] = {
        "pubmed", "europepmc_med", "europepmc_pmc", "europepmc"
    }
    parts = source_database.lower().split("+") if source_database else []
    return any(p.strip() in _BIOMEDICAL_SOURCES for p in parts)


def deduplicate_articles(
    articles: List[Article],
    fuzzy_threshold: int = FUZZY_TITLE_THRESHOLD,
) -> Tuple[List[Article], List[Dict]]:
    """
    Deduplica una lista de artículos.

    Aplica las siguientes estrategias en orden de prioridad:
    1. Fingerprint idéntico (DOI o PMID como componente principal)
    2. DOI exacto (normalizado)
    3. PMID exacto
    4. PMCID exacto
    5. Similitud de título ≥ fuzzy_threshold (token_sort_ratio)

    Cuando se detecta un duplicado:
    - Se marca article.is_duplicate = True
    - Se registra article.duplicate_group_id = fingerprint del primario
    - Se enriquece el primario con metadatos del duplicado que falten

    Args:
        articles:        Lista de artículos a deduplicar.
        fuzzy_threshold: Umbral de similitud de título (0-100).

    Returns:
        (unique_articles, duplicate_pairs)
        - unique_articles:  Lista de artículos únicos (primarios). Modificados in-place.
        - duplicate_pairs:  Lista de dicts con información del match.
    """
    seen_doi:         Dict[str, int] = {}  # doi → índice en `unique`
    seen_pmid:        Dict[str, int] = {}
    seen_pmcid:       Dict[str, int] = {}
    seen_fingerprint: Dict[str, int] = {}

    unique:          List[Article] = []
    duplicate_pairs: List[Dict]    = []

    for article in articles:
        dup_idx = _find_duplicate(
            article, unique,
            seen_doi, seen_pmid, seen_pmcid, seen_fingerprint,
            fuzzy_threshold,
        )

        if dup_idx is not None:
            primary = unique[dup_idx]
            pair = {
                "primary_fingerprint":   primary.fingerprint,
                "duplicate_fingerprint": article.fingerprint,
                "primary_title":         primary.title[:80],
                "duplicate_title":       article.title[:80],
                "primary_source":        primary.source_database,
                "duplicate_source":      article.source_database,
                "reason":                _get_match_reason(primary, article),
                "similarity":            _title_similarity(
                    primary.normalized_title, article.normalized_title
                ),
            }
            duplicate_pairs.append(pair)

            article.is_duplicate       = True
            article.duplicate_group_id = primary.fingerprint

            _merge_metadata(unique[dup_idx], article)
        else:
            if article.doi:
                seen_doi[article.doi] = len(unique)
            if article.pmid:
                seen_pmid[article.pmid] = len(unique)
            if article.pmcid:
                seen_pmcid[article.pmcid] = len(unique)
            seen_fingerprint[article.fingerprint] = len(unique)
            unique.append(article)

    logger.info(
        "Deduplicación: %d originales → %d únicos, %d duplicados",
        len(articles), len(unique), len(duplicate_pairs),
    )
    return unique, duplicate_pairs


def _find_duplicate(
    article:          Article,
    unique:           List[Article],
    seen_doi:         Dict[str, int],
    seen_pmid:        Dict[str, int],
    seen_pmcid:       Dict[str, int],
    seen_fingerprint: Dict[str, int],
    fuzzy_threshold:  int,
) -> Optional[int]:
    """Retorna el índice del artículo duplicado en `unique`, o None."""

    # 1. Fingerprint exacto
    if article.fingerprint in seen_fingerprint:
        return seen_fingerprint[article.fingerprint]

    # 2. DOI exacto (ya normalizado por el modelo)
    if article.doi and article.doi in seen_doi:
        return seen_doi[article.doi]

    # 3. PMID exacto
    if article.pmid and article.pmid in seen_pmid:
        return seen_pmid[article.pmid]

    # 4. PMCID exacto
    if article.pmcid and article.pmcid in seen_pmcid:
        return seen_pmcid[article.pmcid]

    # 5. Similitud de título (solo si el título tiene suficiente longitud)
    if article.normalized_title and len(article.normalized_title) > 10:
        for idx, existing in enumerate(unique):
            if not existing.normalized_title:
                continue
            if _title_similarity(article.normalized_title, existing.normalized_title) >= fuzzy_threshold:
                return idx

    return None


def _title_similarity(title_a: str, title_b: str) -> float:
    """
    Calcula similitud entre dos títulos normalizados.
    Usa token_sort_ratio para ser robusto ante reordenamiento de palabras.
    Retorna 0.0 si alguno de los strings está vacío.
    """
    if not title_a or not title_b:
        return 0.0
    return fuzz.token_sort_ratio(title_a, title_b)


def _get_match_reason(primary: Article, duplicate: Article) -> str:
    if primary.doi and primary.doi == duplicate.doi:
        return f"DOI idéntico: {primary.doi}"
    if primary.pmid and primary.pmid == duplicate.pmid:
        return f"PMID idéntico: {primary.pmid}"
    if primary.pmcid and primary.pmcid == duplicate.pmcid:
        return f"PMCID idéntico: {primary.pmcid}"
    sim = _title_similarity(primary.normalized_title, duplicate.normalized_title)
    return f"Título similar ({sim:.1f}%)"


def _merge_metadata(primary: Article, duplicate: Article) -> None:
    """
    Enriquece el artículo primario con metadatos del duplicado que le falten.
    El primario siempre tiene precedencia sobre el duplicado.

    NOTA sobre source_database:
    Se registran todas las fuentes de origen separadas por "+".
    El formato "pubmed+crossref" es manejado por is_biomedical_source()
    en scoring_service para no perder el flag de indexación biomédica.
    """
    # Identificadores
    if not primary.doi and duplicate.doi:
        primary.doi = duplicate.doi
    if not primary.pmid and duplicate.pmid:
        primary.pmid = duplicate.pmid
    if not primary.pmcid and duplicate.pmcid:
        primary.pmcid = duplicate.pmcid

    # Contenido
    if not primary.abstract and duplicate.abstract:
        primary.abstract = duplicate.abstract
    if not primary.mesh_terms and duplicate.mesh_terms:
        primary.mesh_terms = duplicate.mesh_terms
    if not primary.keywords and duplicate.keywords:
        primary.keywords = duplicate.keywords

    # Acceso
    if not primary.pdf_url and duplicate.pdf_url:
        primary.pdf_url = duplicate.pdf_url

    # Métricas
    if not primary.citation_count and duplicate.citation_count:
        primary.citation_count = duplicate.citation_count

    # Trazabilidad de fuentes
    primary_sources = set(primary.source_database.split("+")) if primary.source_database else set()
    duplicate_sources = set(duplicate.source_database.split("+")) if duplicate.source_database else set()
    new_sources = duplicate_sources - primary_sources
    if new_sources:
        all_sources = sorted(primary_sources | duplicate_sources)
        primary.source_database = "+".join(all_sources)
        logger.debug(
            "Merge: fuentes actualizadas para '%s': %s",
            primary.title[:40], primary.source_database,
        )


def assign_duplicate_groups(articles: List[Article]) -> List[Article]:
    """
    Asigna duplicate_group_id a grupos de potenciales duplicados.
    Modifica los artículos in-place. Útil para revisión manual en la UI.
    """
    _, pairs = deduplicate_articles(articles)

    group_map: Dict[str, str] = {}
    for pair in pairs:
        gid = pair["primary_fingerprint"]
        group_map[pair["primary_fingerprint"]]  = gid
        group_map[pair["duplicate_fingerprint"]] = gid

    for article in articles:
        if article.fingerprint in group_map:
            article.duplicate_group_id = group_map[article.fingerprint]

    return articles
