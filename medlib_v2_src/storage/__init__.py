from .database import (
    init_db, upsert_article, get_all_articles, get_article_by_id,
    update_article_fields, delete_article, get_stats, log_search,
    get_collections, create_collection, get_audit_report,
    get_potential_duplicates,
)

__all__ = [
    "init_db", "upsert_article", "get_all_articles", "get_article_by_id",
    "update_article_fields", "delete_article", "get_stats", "log_search",
    "get_collections", "create_collection", "get_audit_report",
    "get_potential_duplicates",
]
