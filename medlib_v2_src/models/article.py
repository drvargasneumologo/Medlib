"""
Modelos de datos principales con Pydantic.
Esquema normalizado para artículos de múltiples fuentes.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Retorna datetime aware en UTC."""
    return datetime.now(UTC)


class Article(BaseModel):
    """Esquema unificado de artículo científico."""

    model_config = ConfigDict(use_enum_values=True)

    # Identificadores
    id: Optional[int] = None
    source_database: str = ""
    source_record_id: str = ""
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None

    # Contenido
    title: str = ""
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    mesh_terms: List[str] = Field(default_factory=list)

    # Publicación
    journal: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    language: Optional[str] = None
    article_type: Optional[str] = None
    publisher: Optional[str] = None
    issn: Optional[str] = None
    eissn: Optional[str] = None

    # Afiliaciones
    affiliation: Optional[str] = None

    # Acceso
    open_access_status: Optional[str] = None  # open, restricted, unknown
    access_type: Optional[str] = None  # open_access, institutional, restricted, unavailable
    url: Optional[str] = None
    landing_page_url: Optional[str] = None
    pdf_url: Optional[str] = None
    local_pdf_path: Optional[str] = None
    pdf_checksum: Optional[str] = None
    pdf_size_bytes: Optional[int] = None
    pdf_download_date: Optional[datetime] = None
    pdf_status: Optional[str] = None  # available, missing, corrupt, broken_link, restricted

    # Métricas
    citation_count: Optional[int] = None

    # Gestión interna
    date_retrieved: Optional[datetime] = Field(default_factory=utc_now)
    search_query_origin: Optional[str] = None
    collection_name: Optional[str] = "default"
    quality_score: Optional[float] = None
    duplicate_group_id: Optional[str] = None
    is_duplicate: bool = False

    # Estado de lectura
    read_status: str = "pending"  # pending, reading, read, priority, included
    user_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Flags de calidad
    flag_preprint: bool = False
    flag_no_abstract: bool = False
    flag_incomplete_metadata: bool = False
    flag_potential_predatory: bool = False
    flag_parsing_error: bool = False

    # Ficha clínica
    clinical_question: Optional[str] = None
    study_design: Optional[str] = None
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcomes: Optional[str] = None
    main_finding: Optional[str] = None
    limitations: Optional[str] = None
    clinical_utility: Optional[str] = None
    evidence_level: Optional[str] = None

    @field_validator("doi", mode="before")
    @classmethod
    def normalize_doi(cls, value):
        if value:
            value = str(value).strip().lower()
            if value.startswith("https://doi.org/"):
                value = value[len("https://doi.org/"):]
            elif value.startswith("http://doi.org/"):
                value = value[len("http://doi.org/"):]
        return value or None

    @field_validator("pmid", "pmcid", mode="before")
    @classmethod
    def normalize_id(cls, value):
        if value:
            value = str(value).strip()
            return value if value else None
        return None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value):
        if value:
            return re.sub(r"\s+", " ", str(value)).strip()
        return ""

    @property
    def normalized_title(self) -> str:
        """Título normalizado para deduplicación."""
        title = self.title.lower()
        title = re.sub(r"[^\w\s]", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        return title

    @property
    def fingerprint(self) -> str:
        """Hash único para detección de duplicados."""
        parts = []
        if self.doi:
            parts.append(f"doi:{self.doi}")
        if self.pmid:
            parts.append(f"pmid:{self.pmid}")
        if not parts:
            parts.append(f"title:{self.normalized_title[:80]}")
        key = "|".join(parts)
        return hashlib.md5(key.encode()).hexdigest()

    @property
    def authors_str(self) -> str:
        return "; ".join(self.authors)

    @property
    def keywords_str(self) -> str:
        return "; ".join(self.keywords)

    @property
    def mesh_str(self) -> str:
        return "; ".join(self.mesh_terms)

    @property
    def tags_str(self) -> str:
        return "; ".join(self.tags)

    def to_vancouver(self) -> str:
        """Genera referencia estilo Vancouver."""
        authors = self.authors[:6]
        if len(self.authors) > 6:
            authors_str = ", ".join(authors) + " et al"
        else:
            authors_str = ", ".join(authors)

        ref = f"{authors_str}. {self.title}."
        if self.journal:
            ref += f" {self.journal}."
        if self.year:
            ref += f" {self.year}"
        if self.volume:
            ref += f";{self.volume}"
        if self.issue:
            ref += f"({self.issue})"
        if self.pages:
            ref += f":{self.pages}"
        ref += "."
        if self.doi:
            ref += f" doi:{self.doi}"
        elif self.pmid:
            ref += f" PMID:{self.pmid}"
        return ref.strip()


class SearchLog(BaseModel):
    """Registro reproducible de estrategia de búsqueda."""

    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=utc_now)
    source: str
    query: str
    filters: dict = Field(default_factory=dict)
    result_count: int = 0
    saved_count: int = 0
    collection_name: str = "default"
    app_version: str = "0.1.0"
    error: Optional[str] = None
