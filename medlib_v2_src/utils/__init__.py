"""Utilidades generales."""
from __future__ import annotations
import logging
import re
import sys
from pathlib import Path


def setup_logging(level: str = "INFO"):
    """Configura logging con formato limpio."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/medlib.log", encoding="utf-8"),
        ],
    )


def normalize_text(text: str) -> str:
    """Normaliza texto para comparación."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, max_len: int = 120, suffix: str = "…") -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - len(suffix)] + suffix


def safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def current_year() -> int:
    from datetime import UTC, datetime
    return datetime.now(UTC).year
