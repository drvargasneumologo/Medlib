"""
Servicio de scoring de calidad bibliográfica.
Sistema transparente, configurable y documentado.

NOTAS DE DISEÑO
---------------
- El score normaliza sobre la suma de pesos activos (max_possible).
- MIN_ABSTRACT_LENGTH = 20: umbral mínimo para considerar que un abstract
  aporta información.
- is_biomedical_source() delega al dedup_service para manejar correctamente
  el formato compuesto "pubmed+crossref" generado tras un merge.

VALIDACIÓN
----------
- Lógica del scorer: validada mediante tests unitarios offline (sin red).
- Pesos por defecto: juicio experto provisional; no validados bibliométricamente.
- Integración con APIs: pendiente de validación en vivo.
"""
from __future__ import annotations

from typing import Dict, Optional

from models.article import Article
from services.dedup_service import is_biomedical_source

DEFAULT_WEIGHTS: Dict[str, float] = {
    "has_doi":               10,
    "has_abstract":          12,
    "has_pmid":               8,
    "has_pmcid":              6,
    "biomedical_indexed":    10,
    "recent_year":            8,
    "has_fulltext_link":      8,
    "is_open_access":         5,
    "multi_source":           0,   # reservado
    "complete_bibliographic": 8,
    "has_authors":            5,
    "has_journal":            5,
    "high_evidence_type":    10,
    "metadata_integrity":     0,   # reservado
}

HIGH_EVIDENCE_TYPES   = {"meta_analysis", "systematic_review", "rct"}
MEDIUM_EVIDENCE_TYPES = {"clinical_trial", "review", "guideline"}
MIN_ABSTRACT_LENGTH   = 20


def _has_substantial_abstract(article: Article) -> bool:
    """True si el abstract existe y supera el umbral mínimo de longitud."""
    return len((article.abstract or "").strip()) >= MIN_ABSTRACT_LENGTH


def compute_quality_score(
    article: Article,
    weights: Optional[Dict[str, float]] = None,
    current_year: int = 2024,
) -> float:
    """
    Calcula un score de calidad bibliográfica normalizado a 0-100.

    El score se normaliza sobre la suma de los pesos activos (max_possible).
    Cambiar los pesos afecta el denominador: scores con distintos sets de
    pesos no son comparables entre sí directamente.

    Args:
        article:      Artículo a evaluar.
        weights:      Pesos personalizados. Si None, usa DEFAULT_WEIGHTS.
        current_year: Año actual para calcular recencia.

    Returns:
        Float en [0.0, 100.0].
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    max_possible = sum(w.values())
    if max_possible <= 0:
        return 0.0

    score = 0.0

    if article.doi:
        score += w.get("has_doi", 0)

    if _has_substantial_abstract(article):
        score += w.get("has_abstract", 0)

    if article.pmid:
        score += w.get("has_pmid", 0)

    if article.pmcid:
        score += w.get("has_pmcid", 0)

    # Usa is_biomedical_source() para manejar source_database compuesto
    # (e.g. "pubmed+crossref" generado por _merge_metadata)
    if is_biomedical_source(article.source_database or ""):
        score += w.get("biomedical_indexed", 0)

    if article.year:
        age = current_year - article.year
        w_year = w.get("recent_year", 0)
        if age <= 2:
            score += w_year
        elif age <= 5:
            score += w_year * 0.8
        elif age <= 10:
            score += w_year * 0.5

    if article.pdf_url or article.pmcid or article.local_pdf_path:
        score += w.get("has_fulltext_link", 0)

    if article.open_access_status == "open" or article.access_type == "open_access":
        score += w.get("is_open_access", 0)

    if article.journal and article.volume and article.pages:
        score += w.get("complete_bibliographic", 0)
    elif article.journal:
        score += w.get("complete_bibliographic", 0) * 0.5

    if article.authors:
        score += w.get("has_authors", 0)

    if article.journal:
        score += w.get("has_journal", 0)

    w_evid = w.get("high_evidence_type", 0)
    if article.article_type in HIGH_EVIDENCE_TYPES:
        score += w_evid
    elif article.article_type in MEDIUM_EVIDENCE_TYPES:
        score += w_evid * 0.6

    normalized = (score / max_possible) * 100
    return round(min(normalized, 100.0), 1)


def score_batch(
    articles: list,
    weights: Optional[Dict[str, float]] = None,
    current_year: int = 2024,
) -> list:
    """Calcula el score para cada artículo. Modifica in-place y retorna la lista."""
    for article in articles:
        article.quality_score = compute_quality_score(article, weights, current_year)
    return articles


def score_explanation(
    article: Article,
    weights: Optional[Dict[str, float]] = None,
    current_year: int = 2024,
) -> Dict[str, str]:
    """Retorna diccionario con la contribución de cada criterio al score."""
    w = weights if weights is not None else DEFAULT_WEIGHTS
    explanation: Dict[str, str] = {}

    explanation["DOI presente"] = (
        f"+{w['has_doi']} pts" if article.doi else "0 pts (falta DOI)"
    )
    explanation["Abstract presente"] = (
        f"+{w['has_abstract']} pts"
        if _has_substantial_abstract(article)
        else f"0 pts (ausente o < {MIN_ABSTRACT_LENGTH} chars)"
    )
    explanation["PMID presente"] = f"+{w['has_pmid']} pts" if article.pmid else "0 pts"
    explanation["PMCID presente"] = f"+{w['has_pmcid']} pts" if article.pmcid else "0 pts"
    explanation["Indexación biomédica"] = (
        f"+{w['biomedical_indexed']} pts ({article.source_database})"
        if is_biomedical_source(article.source_database or "")
        else f"0 pts (fuente: {article.source_database})"
    )

    if article.year:
        age = current_year - article.year
        w_year = w.get("recent_year", 0)
        if age <= 2:
            explanation["Recencia"] = f"+{w_year} pts (≤2 años)"
        elif age <= 5:
            explanation["Recencia"] = f"+{w_year * 0.8:.1f} pts (≤5 años)"
        elif age <= 10:
            explanation["Recencia"] = f"+{w_year * 0.5:.1f} pts (≤10 años)"
        else:
            explanation["Recencia"] = "0 pts (>10 años)"
    else:
        explanation["Recencia"] = "0 pts (año desconocido)"

    explanation["Texto completo"] = (
        f"+{w.get('has_fulltext_link', 0)} pts"
        if (article.pdf_url or article.pmcid or article.local_pdf_path)
        else "0 pts"
    )
    explanation["Acceso abierto"] = (
        f"+{w.get('is_open_access', 0)} pts"
        if (article.open_access_status == "open" or article.access_type == "open_access")
        else "0 pts"
    )

    w_evid = w.get("high_evidence_type", 0)
    if article.article_type in HIGH_EVIDENCE_TYPES:
        explanation["Tipo de evidencia"] = f"+{w_evid} pts ({article.article_type})"
    elif article.article_type in MEDIUM_EVIDENCE_TYPES:
        explanation["Tipo de evidencia"] = f"+{w_evid * 0.6:.1f} pts ({article.article_type})"
    else:
        explanation["Tipo de evidencia"] = f"0 pts ({article.article_type or 'desconocido'})"

    if article.journal and article.volume and article.pages:
        explanation["Bibliografía completa"] = f"+{w.get('complete_bibliographic', 0)} pts"
    elif article.journal:
        explanation["Bibliografía completa"] = f"+{w.get('complete_bibliographic', 0) * 0.5:.1f} pts (parcial)"
    else:
        explanation["Bibliografía completa"] = "0 pts"

    explanation["SCORE TOTAL"] = f"{compute_quality_score(article, w, current_year):.1f} / 100"
    return explanation
