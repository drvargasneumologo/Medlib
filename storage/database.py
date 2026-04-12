"""
Capa de almacenamiento SQLite.
Maneja creación de esquema, CRUD y consultas.

VALIDACIÓN
----------
- Schema y CRUD: validados mediante tests de integración offline con BD temporal.
- Comportamiento bajo carga o concurrencia alta: no validado.
- Migración de esquema entre versiones: no implementada en MVP.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.article import Article, SearchLog

logger = logging.getLogger(__name__)

# Ruta absoluta basada en la ubicación del módulo, independiente del CWD
_ROOT = Path(__file__).parent.parent
DB_PATH = _ROOT / "data" / "medlib.db"


def get_db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Inicializa el esquema de la base de datos."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_database TEXT NOT NULL DEFAULT '',
                source_record_id TEXT NOT NULL DEFAULT '',
                doi TEXT,
                pmid TEXT,
                pmcid TEXT,
                title TEXT NOT NULL DEFAULT '',
                abstract TEXT,
                authors TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                mesh_terms TEXT DEFAULT '[]',
                journal TEXT,
                year INTEGER,
                month INTEGER,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                language TEXT,
                article_type TEXT,
                publisher TEXT,
                issn TEXT,
                eissn TEXT,
                affiliation TEXT,
                open_access_status TEXT,
                access_type TEXT,
                url TEXT,
                landing_page_url TEXT,
                pdf_url TEXT,
                local_pdf_path TEXT,
                pdf_checksum TEXT,
                pdf_size_bytes INTEGER,
                pdf_download_date TEXT,
                pdf_status TEXT,
                citation_count INTEGER,
                date_retrieved TEXT,
                search_query_origin TEXT,
                collection_name TEXT DEFAULT 'default',
                quality_score REAL,
                duplicate_group_id TEXT,
                is_duplicate INTEGER DEFAULT 0,
                read_status TEXT DEFAULT 'pending',
                user_notes TEXT,
                tags TEXT DEFAULT '[]',
                flag_preprint INTEGER DEFAULT 0,
                flag_no_abstract INTEGER DEFAULT 0,
                flag_incomplete_metadata INTEGER DEFAULT 0,
                flag_potential_predatory INTEGER DEFAULT 0,
                flag_parsing_error INTEGER DEFAULT 0,
                clinical_question TEXT,
                study_design TEXT,
                population TEXT,
                intervention TEXT,
                comparator TEXT,
                outcomes TEXT,
                main_finding TEXT,
                limitations TEXT,
                clinical_utility TEXT,
                evidence_level TEXT,
                fingerprint TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_fingerprint
                ON articles(fingerprint);
            CREATE INDEX IF NOT EXISTS idx_articles_doi ON articles(doi);
            CREATE INDEX IF NOT EXISTS idx_articles_pmid ON articles(pmid);
            CREATE INDEX IF NOT EXISTS idx_articles_collection ON articles(collection_name);
            CREATE INDEX IF NOT EXISTS idx_articles_year ON articles(year);
            CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(quality_score);

            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                query TEXT NOT NULL,
                filters TEXT DEFAULT '{}',
                result_count INTEGER DEFAULT 0,
                saved_count INTEGER DEFAULT 0,
                collection_name TEXT DEFAULT 'default',
                app_version TEXT DEFAULT '0.2.0',
                error TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            INSERT OR IGNORE INTO collections (name, description)
                VALUES ('default', 'Colección principal');
        """)
    logger.info("Base de datos inicializada: %s", get_db_path())


def _article_to_row(a: Article) -> Dict[str, Any]:
    """Convierte un Article a un dict apto para INSERT/UPDATE en SQLite."""
    return {
        "source_database":       a.source_database,
        "source_record_id":      a.source_record_id,
        "doi":                   a.doi,
        "pmid":                  a.pmid,
        "pmcid":                 a.pmcid,
        "title":                 a.title,
        "abstract":              a.abstract,
        "authors":               json.dumps(a.authors, ensure_ascii=False),
        "keywords":              json.dumps(a.keywords, ensure_ascii=False),
        "mesh_terms":            json.dumps(a.mesh_terms, ensure_ascii=False),
        "journal":               a.journal,
        "year":                  a.year,
        "month":                 a.month,
        "volume":                a.volume,
        "issue":                 a.issue,
        "pages":                 a.pages,
        "language":              a.language,
        "article_type":          a.article_type,
        "publisher":             a.publisher,
        "issn":                  a.issn,
        "eissn":                 a.eissn,
        "affiliation":           a.affiliation,
        "open_access_status":    a.open_access_status,
        "access_type":           a.access_type,
        "url":                   a.url,
        "landing_page_url":      a.landing_page_url,
        "pdf_url":               a.pdf_url,
        "local_pdf_path":        a.local_pdf_path,
        "pdf_checksum":          a.pdf_checksum,
        "pdf_size_bytes":        a.pdf_size_bytes,
        "pdf_download_date":     a.pdf_download_date.isoformat() if a.pdf_download_date else None,
        "pdf_status":            a.pdf_status,
        "citation_count":        a.citation_count,
        "date_retrieved":        a.date_retrieved.isoformat() if a.date_retrieved else None,
        "search_query_origin":   a.search_query_origin,
        "collection_name":       a.collection_name or "default",
        "quality_score":         a.quality_score,
        "duplicate_group_id":    a.duplicate_group_id,
        "is_duplicate":          int(a.is_duplicate),
        "read_status":           a.read_status,
        "user_notes":            a.user_notes,
        "tags":                  json.dumps(a.tags, ensure_ascii=False),
        "flag_preprint":         int(a.flag_preprint),
        "flag_no_abstract":      int(a.flag_no_abstract),
        "flag_incomplete_metadata": int(a.flag_incomplete_metadata),
        "flag_potential_predatory": int(a.flag_potential_predatory),
        "flag_parsing_error":    int(a.flag_parsing_error),
        "clinical_question":     a.clinical_question,
        "study_design":          a.study_design,
        "population":            a.population,
        "intervention":          a.intervention,
        "comparator":            a.comparator,
        "outcomes":              a.outcomes,
        "main_finding":          a.main_finding,
        "limitations":           a.limitations,
        "clinical_utility":      a.clinical_utility,
        "evidence_level":        a.evidence_level,
        "fingerprint":           a.fingerprint,
        "updated_at":            datetime.now(UTC).isoformat(),
    }


def _row_to_article(row: sqlite3.Row) -> Article:
    """
    Convierte una fila SQLite a un objeto Article.
    Usa model_fields (Pydantic v2) para filtrar columnas desconocidas.
    """
    d = dict(row)
    for list_field in ("authors", "keywords", "mesh_terms", "tags"):
        raw = d.get(list_field, "[]")
        try:
            d[list_field] = json.loads(raw) if raw else []
        except (json.JSONDecodeError, TypeError):
            d[list_field] = []

    # Convertir enteros SQLite a bool
    d["is_duplicate"] = bool(d.get("is_duplicate", 0))
    for flag in (
        "flag_preprint", "flag_no_abstract", "flag_incomplete_metadata",
        "flag_potential_predatory", "flag_parsing_error",
    ):
        d[flag] = bool(d.get(flag, 0))

    # Filtrar solo campos conocidos por el modelo (Pydantic v2)
    known_fields = set(Article.model_fields.keys())
    filtered = {k: v for k, v in d.items() if k in known_fields}
    return Article(**filtered)


def upsert_article(article: Article) -> tuple[int, bool]:
    """
    Inserta o actualiza un artículo por fingerprint.

    Returns:
        (id, was_inserted): id del registro; True si fue inserción nueva.
    """
    row = _article_to_row(article)
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM articles WHERE fingerprint = ?",
            (article.fingerprint,),
        ).fetchone()

        if existing:
            article_id = existing["id"]
            set_clause = ", ".join(
                f"{k} = :{k}" for k in row if k != "fingerprint"
            )
            conn.execute(
                f"UPDATE articles SET {set_clause} WHERE id = :_id",
                {**row, "_id": article_id},
            )
            return article_id, False
        else:
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            cur = conn.execute(
                f"INSERT INTO articles ({cols}) VALUES ({placeholders})", row
            )
            return cur.lastrowid, True


def get_all_articles(
    collection: Optional[str] = None,
    read_status: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    source: Optional[str] = None,
    min_score: Optional[float] = None,
    search_text: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
) -> List[Article]:
    """Retorna artículos con filtros opcionales. Excluye duplicados marcados."""
    filters = ["is_duplicate = 0"]
    params: Dict[str, Any] = {}

    if collection:
        filters.append("collection_name = :collection")
        params["collection"] = collection
    if read_status:
        filters.append("read_status = :read_status")
        params["read_status"] = read_status
    if year_from:
        filters.append("year >= :year_from")
        params["year_from"] = year_from
    if year_to:
        filters.append("year <= :year_to")
        params["year_to"] = year_to
    if source:
        filters.append("source_database = :source")
        params["source"] = source
    if min_score is not None:
        filters.append("quality_score >= :min_score")
        params["min_score"] = min_score
    if search_text:
        filters.append(
            "(title LIKE :search OR abstract LIKE :search OR authors LIKE :search)"
        )
        params["search"] = f"%{search_text}%"

    where = " AND ".join(filters)
    query = (
        f"SELECT * FROM articles WHERE {where} "
        f"ORDER BY quality_score DESC NULLS LAST, year DESC NULLS LAST "
        f"LIMIT :limit OFFSET :offset"
    )
    params["limit"] = limit
    params["offset"] = offset

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_article(r) for r in rows]


def get_article_by_id(article_id: int) -> Optional[Article]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
    return _row_to_article(row) if row else None


def update_article_fields(article_id: int, fields: Dict[str, Any]):
    """Actualiza campos específicos de un artículo por ID."""
    fields = dict(fields)  # no mutar el argumento original
    fields["updated_at"] = datetime.now(UTC).isoformat()
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE articles SET {set_clause} WHERE id = :_id",
            {**fields, "_id": article_id},
        )


def delete_article(article_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))


def get_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE is_duplicate=0"
        ).fetchone()[0]
        with_pdf = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE local_pdf_path IS NOT NULL AND is_duplicate=0"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE read_status='pending' AND is_duplicate=0"
        ).fetchone()[0]
        priority = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE read_status='priority' AND is_duplicate=0"
        ).fetchone()[0]
        by_collection = conn.execute(
            "SELECT collection_name, COUNT(*) as cnt FROM articles WHERE is_duplicate=0 "
            "GROUP BY collection_name ORDER BY cnt DESC"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source_database, COUNT(*) as cnt FROM articles WHERE is_duplicate=0 "
            "GROUP BY source_database ORDER BY cnt DESC"
        ).fetchall()
        flags = conn.execute(
            """SELECT
                SUM(flag_no_abstract)         AS no_abstract,
                SUM(flag_incomplete_metadata) AS incomplete,
                SUM(flag_preprint)            AS preprints,
                SUM(flag_potential_predatory) AS predatory,
                SUM(is_duplicate)             AS duplicates
               FROM articles"""
        ).fetchone()
        recent_searches = conn.execute(
            "SELECT * FROM search_logs ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

    return {
        "total":          total,
        "with_pdf":       with_pdf,
        "pending":        pending,
        "priority":       priority,
        "by_collection":  [dict(r) for r in by_collection],
        "by_source":      [dict(r) for r in by_source],
        "flags":          dict(flags) if flags else {},
        "recent_searches":[dict(r) for r in recent_searches],
    }


def get_potential_duplicates() -> List[Dict]:
    """Retorna grupos de artículos marcados como posibles duplicados."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT duplicate_group_id, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
            FROM articles
            WHERE duplicate_group_id IS NOT NULL
            GROUP BY duplicate_group_id
            HAVING cnt > 1
            ORDER BY cnt DESC
        """).fetchall()
    return [dict(r) for r in rows]


def log_search(log: SearchLog) -> int:
    row = {
        "timestamp":       log.timestamp.isoformat(),
        "source":          log.source,
        "query":           log.query,
        "filters":         json.dumps(log.filters),
        "result_count":    log.result_count,
        "saved_count":     log.saved_count,
        "collection_name": log.collection_name,
        "app_version":     log.app_version,
        "error":           log.error,
    }
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO search_logs
               (timestamp, source, query, filters, result_count, saved_count,
                collection_name, app_version, error)
               VALUES (:timestamp, :source, :query, :filters, :result_count,
                       :saved_count, :collection_name, :app_version, :error)""",
            row,
        )
        return cur.lastrowid


def get_collections() -> List[str]:
    with get_connection() as conn:
        rows1 = conn.execute("SELECT name FROM collections ORDER BY name").fetchall()
        rows2 = conn.execute(
            "SELECT DISTINCT collection_name FROM articles "
            "WHERE collection_name IS NOT NULL"
        ).fetchall()
    names = {r["name"] for r in rows1} | {r["collection_name"] for r in rows2}
    return sorted(names)


def create_collection(name: str, description: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO collections (name, description) VALUES (?, ?)",
            (name, description),
        )


def get_audit_report() -> Dict[str, Any]:
    with get_connection() as conn:
        missing_doi = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE doi IS NULL AND is_duplicate=0"
        ).fetchone()[0]
        missing_pmid = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE pmid IS NULL AND is_duplicate=0"
        ).fetchone()[0]
        missing_abstract = conn.execute(
            "SELECT COUNT(*) FROM articles "
            "WHERE (abstract IS NULL OR abstract='') AND is_duplicate=0"
        ).fetchone()[0]
        missing_pdf = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE local_pdf_path IS NULL AND is_duplicate=0"
        ).fetchone()[0]
        preprints = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE flag_preprint=1 AND is_duplicate=0"
        ).fetchone()[0]
        predatory = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE flag_potential_predatory=1 AND is_duplicate=0"
        ).fetchone()[0]
        parsing_errors = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE flag_parsing_error=1"
        ).fetchone()[0]
        dup_groups = conn.execute(
            "SELECT COUNT(DISTINCT duplicate_group_id) FROM articles "
            "WHERE duplicate_group_id IS NOT NULL"
        ).fetchone()[0]
        incomplete = conn.execute(
            """SELECT COUNT(*) FROM articles WHERE is_duplicate=0 AND (
                title='' OR title IS NULL OR year IS NULL OR journal IS NULL
            )"""
        ).fetchone()[0]

    return {
        "missing_doi":        missing_doi,
        "missing_pmid":       missing_pmid,
        "missing_abstract":   missing_abstract,
        "missing_pdf":        missing_pdf,
        "preprints":          preprints,
        "predatory_journals": predatory,
        "parsing_errors":     parsing_errors,
        "duplicate_groups":   dup_groups,
        "incomplete_records": incomplete,
    }
