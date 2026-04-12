"""
Conector Unpaywall API.
https://unpaywall.org/products/api

Unpaywall es el servicio más fiable para encontrar versiones legales en
acceso abierto de artículos con DOI. GRATUITO para uso no comercial.

REQUISITO: Email registrado en Unpaywall (mismo CONTACT_EMAIL del .env).
No requiere API key; el email se usa como identificador en la URL.

COBERTURA: ~50 millones de artículos con DOI.
- Si el artículo está en PubMed Central, bioRxiv, SSRN, repositorios
  institucionales, o la web del autor, Unpaywall lo encuentra.
- No garantiza acceso a todos los artículos.

USO: Se llama automáticamente al guardar artículos con DOI, para
enriquecer la información de acceso abierto.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def _get(url: str) -> requests.Response:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    time.sleep(0.5)
    return resp


def lookup_oa_by_doi(doi: str) -> Optional[dict]:
    """
    Consulta Unpaywall para un DOI dado.

    Args:
        doi: DOI normalizado (sin https://doi.org/).

    Returns:
        Dict con:
            is_oa (bool): True si hay versión OA disponible.
            oa_status (str): 'gold'|'green'|'hybrid'|'bronze'|'closed'
            best_pdf_url (str|None): URL directa al PDF si existe.
            best_landing_url (str|None): Landing page del artículo OA.
            host_type (str|None): 'publisher'|'repository'
        Retorna None si el DOI no se encuentra o hay error.
    """
    email = os.getenv("CONTACT_EMAIL", "")
    if not email:
        logger.warning(
            "Unpaywall requiere CONTACT_EMAIL en .env. Sin email no se puede consultar."
        )
        return None

    url = f"{UNPAYWALL_BASE}/{doi}?email={email}"
    try:
        resp = _get(url)
        data = resp.json()
    except Exception as exc:
        logger.error("Unpaywall error para DOI %s: %s", doi, exc)
        return None

    is_oa = data.get("is_oa", False)
    oa_status = data.get("oa_status", "unknown")  # gold, green, hybrid, bronze, closed

    best_oa = data.get("best_oa_location") or {}
    pdf_url = best_oa.get("url_for_pdf")
    landing_url = best_oa.get("url_for_landing_page") or best_oa.get("url")
    host_type = best_oa.get("host_type")

    # Si el mejor OA no tiene PDF, buscar en todas las ubicaciones
    if not pdf_url:
        for loc in data.get("oa_locations", []):
            if loc.get("url_for_pdf"):
                pdf_url = loc["url_for_pdf"]
                break

    logger.info(
        "Unpaywall DOI %s: is_oa=%s status=%s pdf=%s",
        doi, is_oa, oa_status, "SÍ" if pdf_url else "NO"
    )

    return {
        "is_oa":            is_oa,
        "oa_status":        oa_status,
        "best_pdf_url":     pdf_url,
        "best_landing_url": landing_url,
        "host_type":        host_type,
    }


def enrich_article_with_unpaywall(article) -> bool:
    """
    Enriquece un Article con información de acceso abierto desde Unpaywall.
    Modifica el artículo in-place.

    Args:
        article: objeto Article con atributo doi.

    Returns:
        True si se encontró información útil, False en caso contrario.
    """
    if not article.doi:
        return False

    oa_info = lookup_oa_by_doi(article.doi)
    if not oa_info:
        return False

    if oa_info["is_oa"]:
        article.open_access_status = "open"
        article.access_type = "open_access"

        if oa_info["best_pdf_url"] and not article.pdf_url:
            article.pdf_url = oa_info["best_pdf_url"]

        if oa_info["best_landing_url"] and not article.landing_page_url:
            article.landing_page_url = oa_info["best_landing_url"]
    else:
        if article.open_access_status not in ("open",):
            article.open_access_status = oa_info["oa_status"]
            article.access_type = "restricted"

    return True
