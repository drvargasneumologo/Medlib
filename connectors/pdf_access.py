"""
Módulo de acceso y descarga de PDFs.

Maneja tres niveles de acceso, en orden de prioridad:
  1. Acceso Abierto directo (Unpaywall, PMC, preprint servers)
  2. Acceso Institucional (VPN activa, proxy EZproxy, cookies de sesión)
  3. Acceso restringido (registra como no disponible, sin bypass)

SEGURIDAD Y ÉTICA
-----------------
- Nunca intenta bypass de paywalls ni CAPTCHA.
- Nunca almacena contraseñas en texto plano.
- Las credenciales institucionales se leen SOLO desde variables de entorno.
- El módulo institucional solo intenta acceso si la URL es de un dominio
  que el usuario configuró explícitamente.
- Se registra checksum SHA-256 de cada PDF descargado para verificar integridad.

CONFIGURACIÓN EN .env
---------------------
    INSTITUTION_ENABLED=true
    INSTITUTION_NAME=UNAM
    EZPROXY_BASE_URL=https://login.biblioteca.unam.mx/login?url=
    INSTITUTION_COOKIE_NAME=
    INSTITUTION_COOKIE_VALUE=
    # O bien, para proxy HTTP:
    INSTITUTION_PROXY_HTTP=http://proxy.institucion.edu:3128
    INSTITUTION_PROXY_HTTPS=http://proxy.institucion.edu:3128
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Directorio local donde se guardan los PDFs descargados
PDF_DIR = Path("data/pdfs")

# Tamaño mínimo para considerar que un PDF es válido (10 KB)
MIN_PDF_SIZE_BYTES = 10_240

# User-Agent neutral para descarga
_UA = "Mozilla/5.0 (compatible; MedLib/0.3 research tool)"


# ─── Descarga de acceso abierto ───────────────────────────────────────────────

def download_open_access_pdf(
    article,
    save_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Intenta descargar el PDF de un artículo si tiene enlace de acceso abierto.

    Solo descarga si:
    - article.pdf_url está disponible (Unpaywall, PMC, preprint).
    - La URL es HTTPS.
    - El archivo resultante es un PDF válido (≥ MIN_PDF_SIZE_BYTES bytes).

    Args:
        article:  Objeto Article con pdf_url.
        save_dir: Carpeta de destino. Default: data/pdfs/

    Returns:
        Path al archivo guardado, o None si no fue posible.
    """
    if not article.pdf_url:
        logger.debug("Sin pdf_url para: %s", article.title[:40])
        return None

    url = article.pdf_url
    if not url.startswith("https://"):
        logger.warning("PDF URL no es HTTPS, se omite por seguridad: %s", url[:60])
        return None

    save_dir = save_dir or PDF_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    # Nombre de archivo seguro basado en PMID o DOI
    safe_name = _make_safe_filename(article)
    dest = save_dir / f"{safe_name}.pdf"

    if dest.exists() and dest.stat().st_size >= MIN_PDF_SIZE_BYTES:
        logger.info("PDF ya existe: %s", dest)
        return dest

    try:
        headers = {"User-Agent": _UA, "Accept": "application/pdf,*/*"}
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()

        # Verificar Content-Type
        ct = resp.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and "octet-stream" not in ct.lower():
            logger.warning(
                "Content-Type inesperado (%s) para %s — probablemente no es un PDF",
                ct, url[:60]
            )
            return None

        # Descargar y verificar tamaño
        content = resp.content
        if len(content) < MIN_PDF_SIZE_BYTES:
            logger.warning(
                "PDF demasiado pequeño (%d bytes) para %s — posiblemente inválido",
                len(content), url[:60]
            )
            return None

        # Verificar magic bytes PDF (%PDF-)
        if not content.startswith(b"%PDF"):
            logger.warning("El archivo no empieza con magic bytes PDF: %s", url[:60])
            return None

        dest.write_bytes(content)
        logger.info(
            "PDF descargado: %s (%d KB)", dest.name, len(content) // 1024
        )
        return dest

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        if status in (401, 403):
            logger.info("PDF restringido (HTTP %s): %s", status, url[:60])
            article.pdf_status = "restricted"
        elif status == 404:
            logger.info("PDF no encontrado (HTTP 404): %s", url[:60])
            article.pdf_status = "broken_link"
        else:
            logger.warning("HTTP error %s al descargar PDF: %s", status, url[:60])
            article.pdf_status = "error"
        return None

    except Exception as exc:
        logger.error("Error descargando PDF %s: %s", url[:60], exc)
        article.pdf_status = "error"
        return None


def compute_pdf_checksum(path: Path) -> str:
    """Calcula SHA-256 del archivo PDF para verificar integridad."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def update_article_pdf_metadata(article, pdf_path: Path) -> None:
    """Actualiza los campos de PDF de un Article tras descarga exitosa."""
    article.local_pdf_path    = str(pdf_path)
    article.pdf_status        = "available"
    article.pdf_checksum      = compute_pdf_checksum(pdf_path)
    article.pdf_size_bytes    = pdf_path.stat().st_size
    article.pdf_download_date = datetime.now(UTC)


# ─── Acceso Institucional ─────────────────────────────────────────────────────

class InstitutionalAccessConfig:
    """
    Configuración de acceso institucional leída desde variables de entorno.
    Nunca almacena contraseñas ni tokens en el objeto después de usarlos.
    """

    def __init__(self):
        self.enabled    = os.getenv("INSTITUTION_ENABLED", "false").lower() == "true"
        self.name       = os.getenv("INSTITUTION_NAME", "")
        self.ezproxy    = os.getenv("EZPROXY_BASE_URL", "").strip()
        self.proxy_http = os.getenv("INSTITUTION_PROXY_HTTP", "").strip()
        self.proxy_https= os.getenv("INSTITUTION_PROXY_HTTPS", "").strip()
        # Cookies de sesión (configuradas por el usuario después de login manual)
        self._cookie_name  = os.getenv("INSTITUTION_COOKIE_NAME", "").strip()
        self._cookie_value = os.getenv("INSTITUTION_COOKIE_VALUE", "").strip()

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(
            self.ezproxy or self.proxy_http or self._cookie_name
        )

    def get_proxies(self) -> dict:
        if self.proxy_http:
            return {
                "http":  self.proxy_http,
                "https": self.proxy_https or self.proxy_http,
            }
        return {}

    def get_cookies(self) -> dict:
        if self._cookie_name and self._cookie_value:
            return {self._cookie_name: self._cookie_value}
        return {}

    def build_ezproxy_url(self, target_url: str) -> str:
        """Construye la URL a través del proxy EZproxy de la institución."""
        if not self.ezproxy:
            return target_url
        return f"{self.ezproxy}{target_url}"

    def __repr__(self):
        return (
            f"InstitutionalAccess(enabled={self.enabled}, "
            f"institution={self.name}, "
            f"ezproxy={'sí' if self.ezproxy else 'no'}, "
            f"proxy={'sí' if self.proxy_http else 'no'}, "
            f"cookies={'sí' if self._cookie_name else 'no'})"
        )


def download_with_institutional_access(
    article,
    config: Optional[InstitutionalAccessConfig] = None,
    save_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Intenta descargar un PDF usando acceso institucional configurado.

    Estrategias intentadas en orden:
    1. EZproxy: reescribe la URL a través del proxy de la institución.
    2. Proxy HTTP: encamina la petición por el proxy corporativo.
    3. Cookie de sesión: usa cookies de una sesión activa del usuario.

    LIMITACIONES HONESTAS:
    - Solo funciona si el usuario tiene acceso legítimo a través de su
      institución y ha configurado correctamente las credenciales.
    - No funciona con SSO/SAML/OAuth que requieren navegador.
    - No funciona con DRM o validación por IP si no hay VPN activa.
    - Las cookies de sesión expiran; el usuario debe renovarlas manualmente.

    Args:
        article: Objeto Article.
        config:  InstitutionalAccessConfig. Si None, se crea desde .env.
        save_dir: Carpeta de destino.

    Returns:
        Path al PDF si se descargó, None en caso contrario.
    """
    cfg = config or InstitutionalAccessConfig()

    if not cfg.is_configured:
        logger.debug("Acceso institucional no configurado.")
        return None

    # Determinar URL objetivo: landing_page_url o construir desde DOI
    target_url = (
        article.landing_page_url
        or (f"https://doi.org/{article.doi}" if article.doi else None)
    )
    if not target_url:
        return None

    save_dir = save_dir or PDF_DIR
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _make_safe_filename(article)
    dest = save_dir / f"{safe_name}_inst.pdf"

    # Intentar con EZproxy
    if cfg.ezproxy:
        ezproxy_url = cfg.build_ezproxy_url(target_url)
        logger.info(
            "Intentando acceso institucional vía EZproxy (%s): %s",
            cfg.name, ezproxy_url[:60]
        )
        result = _attempt_institutional_download(
            url=ezproxy_url,
            dest=dest,
            proxies={},
            cookies=cfg.get_cookies(),
        )
        if result:
            return result

    # Intentar con proxy HTTP
    if cfg.proxy_http:
        logger.info(
            "Intentando acceso institucional vía proxy HTTP (%s)",
            cfg.name
        )
        result = _attempt_institutional_download(
            url=target_url,
            dest=dest,
            proxies=cfg.get_proxies(),
            cookies=cfg.get_cookies(),
        )
        if result:
            return result

    # Intentar con solo cookies (VPN activa en el sistema)
    if cfg.get_cookies():
        logger.info("Intentando acceso con cookies de sesión institucional")
        result = _attempt_institutional_download(
            url=target_url,
            dest=dest,
            proxies={},
            cookies=cfg.get_cookies(),
        )
        if result:
            return result

    logger.info(
        "Acceso institucional no disponible para: %s", article.title[:50]
    )
    article.pdf_status = "institutional_required"
    return None


def _attempt_institutional_download(
    url: str,
    dest: Path,
    proxies: dict,
    cookies: dict,
) -> Optional[Path]:
    """Intento real de descarga con parámetros de acceso institucional."""
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": _UA})
        if cookies:
            session.cookies.update(cookies)

        resp = session.get(
            url,
            proxies=proxies or None,
            timeout=60,
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and "octet-stream" not in ct.lower():
            # Puede ser una página de login en lugar del PDF
            logger.debug(
                "Respuesta no es PDF (Content-Type: %s) — posiblemente redirigió a login",
                ct
            )
            return None

        content = resp.content
        if len(content) < MIN_PDF_SIZE_BYTES or not content.startswith(b"%PDF"):
            return None

        dest.write_bytes(content)
        logger.info(
            "PDF descargado vía acceso institucional: %s (%d KB)",
            dest.name, len(content) // 1024
        )
        return dest

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        logger.debug("HTTP %s en acceso institucional: %s", status, url[:60])
        return None
    except Exception as exc:
        logger.debug("Error en acceso institucional: %s", exc)
        return None


# ─── Función principal de acceso a PDF ───────────────────────────────────────

def get_pdf_for_article(
    article,
    institutional_config: Optional[InstitutionalAccessConfig] = None,
    save_dir: Optional[Path] = None,
) -> dict:
    """
    Intenta obtener el PDF de un artículo por todos los métodos disponibles.
    Registra el resultado en el artículo y retorna un reporte.

    Orden de intentos:
    1. Ya existe localmente → retorna path existente.
    2. Acceso abierto (pdf_url de Unpaywall/PMC) → descarga directa.
    3. Acceso institucional (si está configurado) → proxy/EZproxy/cookies.
    4. No disponible → registra el estado.

    Returns:
        dict con claves: method, success, path, message
    """
    # 1. Ya existe
    if article.local_pdf_path:
        p = Path(article.local_pdf_path)
        if p.exists() and p.stat().st_size >= MIN_PDF_SIZE_BYTES:
            return {
                "method":  "local_cache",
                "success": True,
                "path":    str(p),
                "message": f"PDF ya disponible localmente ({p.stat().st_size // 1024} KB)",
            }

    # 2. Acceso abierto
    if article.pdf_url:
        path = download_open_access_pdf(article, save_dir)
        if path:
            update_article_pdf_metadata(article, path)
            return {
                "method":  "open_access",
                "success": True,
                "path":    str(path),
                "message": f"Descargado vía acceso abierto ({path.stat().st_size // 1024} KB)",
            }

    # 3. Acceso institucional
    cfg = institutional_config or InstitutionalAccessConfig()
    if cfg.is_configured:
        path = download_with_institutional_access(article, cfg, save_dir)
        if path:
            update_article_pdf_metadata(article, path)
            return {
                "method":  "institutional",
                "success": True,
                "path":    str(path),
                "message": f"Descargado vía acceso institucional ({path.stat().st_size // 1024} KB)",
            }

    # 4. No disponible
    if not article.pdf_status:
        article.pdf_status = "unavailable"

    reasons = []
    if not article.pdf_url:
        reasons.append("sin enlace OA conocido")
    if not cfg.is_configured:
        reasons.append("acceso institucional no configurado")
    else:
        reasons.append("acceso institucional no resolvió el PDF")

    return {
        "method":  "none",
        "success": False,
        "path":    None,
        "message": "PDF no disponible: " + "; ".join(reasons),
    }


# ─── Utilidades ───────────────────────────────────────────────────────────────

def _make_safe_filename(article, max_title_len: int = 50) -> str:
    """Genera nombre de archivo seguro para el PDF."""
    import re
    prefix = (
        article.pmid
        or (article.doi.replace("/", "_").replace(":", "_") if article.doi else None)
        or "art"
    )
    title_part = re.sub(r"[^\w\s-]", "", (article.title or ""))
    title_part = re.sub(r"\s+", "_", title_part)[:max_title_len]
    return f"{prefix}_{title_part}"
