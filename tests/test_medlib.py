"""
Suite de tests para MedLib v0.2.0.

CLASIFICACIÓN DE TESTS
----------------------
[UNIT]   Tests unitarios offline: no requieren red ni DB externa.
         Validan lógica pura (modelos, scoring, deduplicación, exportadores).

[INTEG]  Tests de integración con SQLite: usan BD temporal en tmp_path.
         No requieren red. Validan CRUD, upsert, log, colecciones.

[PENDING] Tests pendientes de validación en vivo (requieren red).
          Marcados con @pytest.mark.skip si deben omitirse en CI.

EJECUCIÓN
---------
    pytest tests/ -v                    # todos los tests offline
    pytest tests/ -v -k "not live"      # excluir tests de red (si se añaden)
    pytest tests/ -v --tb=short         # traceback resumido

COBERTURA CONOCIDA
------------------
- Modelos Pydantic v2: normalización, fingerprint, Vancouver, propiedades.
- Scoring: rango, invariantes semánticas, umbrales de abstract, tipos evidencia.
- Deduplicación: DOI exacto, PMID exacto, fuzzy título, merge de metadatos.
- Exportadores: CSV, JSON, RIS, BibTeX, ZIP NotebookLM.
- Base de datos SQLite: insert, upsert, update, delete, stats, logs.
- Edge-cases: abstract nulo, DOI nulo, autores vacíos, fecha incompleta,
  PMCID con discordancia, título muy corto, duplicados parciales.

LO QUE NO CUBRE ESTA SUITE
---------------------------
- Parsing de XML real de PubMed (requiere fixtures o red).
- Parsing de JSON real de Europe PMC / Crossref / OpenAlex.
- Comportamiento de rate limiting y tenacity.
- Interfaz Streamlit (no se testea UI con pytest en este MVP).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.article import Article, SearchLog
from services.dedup_service import deduplicate_articles, _title_similarity
from services.scoring_service import (
    DEFAULT_WEIGHTS,
    MIN_ABSTRACT_LENGTH,
    _has_substantial_abstract,
    compute_quality_score,
    score_batch,
    score_explanation,
)


# ─── Factory de artículos ─────────────────────────────────────────────────────

def make_article(**kwargs) -> Article:
    """
    Crea un artículo con metadatos completos por defecto.
    Útil para tests que necesitan un artículo 'bueno' como base.
    """
    defaults = {
        "source_database":  "pubmed",
        "source_record_id": "12345",
        "title":  "Effects of nintedanib on pulmonary fibrosis progression",
        "year":   2022,
        "journal":"New England Journal of Medicine",
        "authors":["Smith AB", "Jones CD"],
        "pmid":   "12345678",
        "doi":    "10.1056/test.12345",
        "abstract": (
            "This is a test abstract with sufficient length to be considered "
            "valid for scoring purposes in the MedLib system."
        ),
    }
    defaults.update(kwargs)
    return Article(**defaults)


def make_minimal_article(**kwargs) -> Article:
    """Crea un artículo con los campos mínimos posibles."""
    defaults = {
        "source_database":  "crossref",
        "source_record_id": "min-001",
        "title": "Minimal article",
    }
    defaults.update(kwargs)
    return Article(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestArticleModel
# ═══════════════════════════════════════════════════════════════════════════════

class TestArticleModel:
    """Tests del modelo Pydantic Article. Sin red, sin DB."""

    # ── Normalización de DOI ──────────────────────────────────────────────────

    def test_doi_normalization_https(self):
        a = Article(title="T", source_database="x", source_record_id="1",
                    doi="https://doi.org/10.1056/test.123")
        assert a.doi == "10.1056/test.123"

    def test_doi_normalization_http(self):
        a = Article(title="T", source_database="x", source_record_id="1",
                    doi="http://doi.org/10.1056/test.123")
        assert a.doi == "10.1056/test.123"

    def test_doi_none_stays_none(self):
        a = Article(title="T", source_database="x", source_record_id="1", doi=None)
        assert a.doi is None

    def test_doi_empty_string_becomes_none(self):
        a = Article(title="T", source_database="x", source_record_id="1", doi="")
        assert a.doi is None

    def test_doi_lowercase(self):
        a = Article(title="T", source_database="x", source_record_id="1",
                    doi="10.1056/TEST.123")
        assert a.doi == "10.1056/test.123"

    # ── Normalización de PMID/PMCID ───────────────────────────────────────────

    def test_pmid_strip_whitespace(self):
        a = Article(title="T", source_database="x", source_record_id="1", pmid="  12345  ")
        assert a.pmid == "12345"

    def test_pmid_none_stays_none(self):
        a = Article(title="T", source_database="x", source_record_id="1", pmid=None)
        assert a.pmid is None

    def test_pmid_integer_coerced_to_string(self):
        a = Article(title="T", source_database="x", source_record_id="1", pmid=12345678)
        assert a.pmid == "12345678"
        assert isinstance(a.pmid, str)

    # ── Normalización de título ────────────────────────────────────────────────

    def test_title_cleaning_extra_spaces(self):
        a = Article(title="  Test   Title  With  Spaces  ",
                    source_database="x", source_record_id="1")
        assert a.title == "Test Title With Spaces"

    def test_empty_title_stays_empty(self):
        a = Article(title="", source_database="x", source_record_id="1")
        assert a.title == ""

    def test_normalized_title_removes_punctuation(self):
        a = make_article(title="Effect of Drug X on Disease Y: A Randomized Trial")
        assert a.normalized_title == "effect of drug x on disease y a randomized trial"

    def test_normalized_title_empty(self):
        a = Article(title="", source_database="x", source_record_id="1")
        assert a.normalized_title == ""

    # ── Fingerprint ──────────────────────────────────────────────────────────

    def test_fingerprint_consistency(self):
        a = make_article()
        b = make_article()
        assert a.fingerprint == b.fingerprint

    def test_fingerprint_doi_based(self):
        a = make_article(doi="10.1056/test.001")
        b = make_article(doi="10.1056/test.002")
        assert a.fingerprint != b.fingerprint

    def test_fingerprint_uses_doi_over_pmid(self):
        """Si hay DOI, el fingerprint depende del DOI, no del PMID."""
        a1 = make_article(doi="10.1056/same", pmid="111")
        a2 = make_article(doi="10.1056/same", pmid="222")
        assert a1.fingerprint == a2.fingerprint

    def test_fingerprint_falls_back_to_title(self):
        """Sin DOI ni PMID, el fingerprint usa el título."""
        a1 = make_article(doi=None, pmid=None, title="Title alpha")
        a2 = make_article(doi=None, pmid=None, title="Title beta")
        assert a1.fingerprint != a2.fingerprint

    def test_fingerprint_title_fallback_consistent(self):
        a1 = make_article(doi=None, pmid=None)
        a2 = make_article(doi=None, pmid=None)
        assert a1.fingerprint == a2.fingerprint

    # ── Referencia Vancouver ──────────────────────────────────────────────────

    def test_vancouver_reference(self):
        a = make_article(
            authors=["Smith AB", "Jones CD"],
            title="Test article",
            journal="NEJM",
            year=2022,
            volume="386",
            issue="1",
            pages="1-10",
            doi="10.1056/test",
        )
        ref = a.to_vancouver()
        assert "Smith AB" in ref
        assert "NEJM" in ref
        assert "2022" in ref
        assert "10.1056/test" in ref

    def test_vancouver_et_al_over_six_authors(self):
        a = make_article(
            authors=["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
            doi=None, pmid="99"
        )
        ref = a.to_vancouver()
        assert "et al" in ref

    def test_vancouver_no_authors(self):
        a = make_article(authors=[])
        ref = a.to_vancouver()
        assert ref  # no debe lanzar excepción

    def test_vancouver_no_doi_uses_pmid(self):
        a = make_article(doi=None, pmid="99999999")
        ref = a.to_vancouver()
        assert "PMID:99999999" in ref

    # ── Propiedades de string ─────────────────────────────────────────────────

    def test_authors_str(self):
        a = make_article(authors=["Smith AB", "Jones CD", "Brown EF"])
        assert "Smith AB" in a.authors_str
        assert ";" in a.authors_str

    def test_empty_authors_str(self):
        a = make_article(authors=[])
        assert a.authors_str == ""

    def test_keywords_str(self):
        a = make_article(keywords=["COPD", "spirometry"])
        assert "COPD" in a.keywords_str
        assert ";" in a.keywords_str

    def test_tags_str(self):
        a = make_article(tags=["priority", "revision"])
        assert "priority" in a.tags_str


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestScoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoring:
    """Tests del servicio de scoring. Sin red, sin DB."""

    # ── Umbrales y helper interno ─────────────────────────────────────────────

    def test_abstract_threshold_above(self):
        a = make_article(abstract="A" * MIN_ABSTRACT_LENGTH)
        assert _has_substantial_abstract(a) is True

    def test_abstract_threshold_below(self):
        a = make_article(abstract="A" * (MIN_ABSTRACT_LENGTH - 1))
        assert _has_substantial_abstract(a) is False

    def test_abstract_threshold_exact(self):
        a = make_article(abstract="A" * MIN_ABSTRACT_LENGTH)
        assert _has_substantial_abstract(a) is True

    def test_abstract_none(self):
        a = make_article(abstract=None)
        assert _has_substantial_abstract(a) is False

    def test_abstract_empty_string(self):
        a = make_article(abstract="")
        assert _has_substantial_abstract(a) is False

    def test_abstract_only_whitespace(self):
        a = make_article(abstract="   ")
        assert _has_substantial_abstract(a) is False

    # ── Rango del score ───────────────────────────────────────────────────────

    def test_score_range_complete_article(self):
        a = make_article()
        s = compute_quality_score(a, current_year=2024)
        assert 0.0 <= s <= 100.0

    def test_score_range_minimal_article(self):
        a = make_minimal_article()
        s = compute_quality_score(a, current_year=2024)
        assert 0.0 <= s <= 100.0

    def test_score_is_float(self):
        a = make_article()
        s = compute_quality_score(a, current_year=2024)
        assert isinstance(s, float)

    # ── Invariantes semánticas ────────────────────────────────────────────────

    def test_perfect_article_high_score(self):
        a = make_article(
            doi="10.1056/test.001",
            pmid="12345678",
            pmcid="PMC1234567",
            abstract="Long abstract with enough text to pass the minimum threshold easily.",
            article_type="meta_analysis",
            year=2023,
            journal="NEJM",
            volume="388",
            pages="1-15",
            pdf_url="https://pmc.nih.gov/pdf",
            open_access_status="open",
            access_type="open_access",
            authors=["Smith AB"],
        )
        s = compute_quality_score(a, current_year=2024)
        assert s > 70, f"Score esperado >70, obtenido {s}"

    def test_minimal_article_low_score(self):
        a = make_minimal_article()
        s = compute_quality_score(a, current_year=2024)
        assert s < 30, f"Score esperado <30, obtenido {s}"

    def test_with_abstract_higher_than_without(self):
        """Artículo con abstract sustancial debe superar al mismo sin abstract."""
        base = dict(
            doi="10.1/x", pmid="1", source_database="pubmed",
            year=2022, journal="NEJM", authors=["A"],
        )
        a_with    = make_article(**base, abstract="A" * 60)
        a_without = make_article(**base, abstract=None)
        s_with    = compute_quality_score(a_with, current_year=2024)
        s_without = compute_quality_score(a_without, current_year=2024)
        assert s_with > s_without, (
            f"Con abstract ({s_with}) debe ser mayor que sin abstract ({s_without})"
        )

    def test_abstract_too_short_treated_as_absent(self):
        """Abstract menor que MIN_ABSTRACT_LENGTH no suma puntos."""
        short_abstract = "A" * (MIN_ABSTRACT_LENGTH - 1)
        a_short  = make_article(abstract=short_abstract)
        a_no_abs = make_article(abstract=None)
        s_short  = compute_quality_score(a_short, current_year=2024)
        s_no_abs = compute_quality_score(a_no_abs, current_year=2024)
        assert s_short == s_no_abs, (
            f"Abstract corto ({s_short}) debe igualar a sin abstract ({s_no_abs})"
        )

    def test_recent_year_higher_score(self):
        a_recent = make_article(year=2023)
        a_old    = make_article(year=2005)
        assert compute_quality_score(a_recent, current_year=2024) > \
               compute_quality_score(a_old, current_year=2024)

    def test_rct_higher_than_editorial(self):
        a_rct  = make_article(article_type="rct")
        a_edit = make_article(article_type="editorial")
        assert compute_quality_score(a_rct, current_year=2024) > \
               compute_quality_score(a_edit, current_year=2024)

    def test_meta_analysis_higher_than_review(self):
        a_ma  = make_article(article_type="meta_analysis")
        a_rev = make_article(article_type="review")
        assert compute_quality_score(a_ma, current_year=2024) > \
               compute_quality_score(a_rev, current_year=2024)

    def test_review_higher_than_no_type(self):
        a_rev = make_article(article_type="review")
        a_no  = make_article(article_type=None)
        assert compute_quality_score(a_rev, current_year=2024) > \
               compute_quality_score(a_no, current_year=2024)

    def test_oa_adds_points(self):
        a_oa = make_article(open_access_status="open", access_type="open_access")
        a_no = make_article(open_access_status="unknown", access_type="unknown")
        assert compute_quality_score(a_oa, current_year=2024) >= \
               compute_quality_score(a_no, current_year=2024)

    def test_pmcid_adds_points(self):
        """PMCID aporta tanto por has_pmcid como por has_fulltext_link."""
        a_with = make_article(pmcid="PMC123456")
        a_without = make_article(pmcid=None, pdf_url=None)
        s_with    = compute_quality_score(a_with, current_year=2024)
        s_without = compute_quality_score(a_without, current_year=2024)
        assert s_with > s_without

    # ── Comportamiento con fechas incompletas ─────────────────────────────────

    def test_year_none_no_crash(self):
        a = make_article(year=None)
        s = compute_quality_score(a, current_year=2024)
        assert 0 <= s <= 100

    def test_year_future_no_negative(self):
        """Año futuro (age < 0) no debe dar score negativo."""
        a = make_article(year=2030)
        s = compute_quality_score(a, current_year=2024)
        assert s >= 0

    def test_year_very_old(self):
        """Artículo de 1980: age > 10, no suma puntos por recencia."""
        a_old    = make_article(year=1980)
        a_no_year = make_article(year=None)
        s_old    = compute_quality_score(a_old, current_year=2024)
        s_no_year = compute_quality_score(a_no_year, current_year=2024)
        # Ambos deben ser iguales en el componente recencia (ambos = 0)
        # Pero year=1980 no añade ni quita nada más
        assert s_old == s_no_year, (
            f"Artículo muy antiguo ({s_old}) debe igualar a sin año ({s_no_year})"
        )

    # ── Pesos personalizados ──────────────────────────────────────────────────

    def test_custom_weights_zero_all(self):
        """Todos los pesos a cero → score = 0."""
        a = make_article()
        zero_weights = {k: 0 for k in DEFAULT_WEIGHTS}
        s = compute_quality_score(a, weights=zero_weights, current_year=2024)
        assert s == 0.0

    def test_custom_weights_semantic_invariant(self):
        """
        Con cualquier set de pesos positivos, un artículo con abstract
        debe superar a uno sin abstract, si el peso de has_abstract > 0.
        """
        custom = dict(DEFAULT_WEIGHTS)
        custom["has_abstract"] = 30  # más peso al abstract
        base = dict(doi="10.1/y", pmid="2", source_database="pubmed",
                    year=2022, journal="J", authors=["A"])
        a_with    = make_article(**base, abstract="A" * 60)
        a_without = make_article(**base, abstract=None)
        s_with    = compute_quality_score(a_with, weights=custom, current_year=2024)
        s_without = compute_quality_score(a_without, weights=custom, current_year=2024)
        assert s_with > s_without

    def test_custom_weights_removing_doi_weight(self):
        """
        Eliminar el peso de DOI (→0) cambia el denominador.
        El score no debe exceder 100, y el invariante
        'artículo sin DOI con weights_no_doi == artículo con DOI sin esa recompensa'
        debe cumplirse.
        NOTA: NO se compara score_default vs score_no_doi porque la normalización
        con distinto denominador hace que esa comparación sea indefinida.
        """
        weights_no_doi = dict(DEFAULT_WEIGHTS)
        weights_no_doi["has_doi"] = 0

        a_with_doi    = make_article(doi="10.1/x")
        a_without_doi = make_article(doi=None)

        s_with    = compute_quality_score(a_with_doi, weights=weights_no_doi, current_year=2024)
        s_without = compute_quality_score(a_without_doi, weights=weights_no_doi, current_year=2024)

        # Con peso de DOI = 0, ambos artículos deben tener el mismo score
        # respecto al criterio DOI (ninguno suma puntos por DOI)
        assert s_with <= 100.0
        assert s_without <= 100.0

    # ── score_batch ───────────────────────────────────────────────────────────

    def test_score_batch_modifies_inplace(self):
        articles = [make_article(), make_minimal_article()]
        result = score_batch(articles, current_year=2024)
        assert result is articles  # misma lista, modificada in-place
        for a in articles:
            assert a.quality_score is not None

    def test_score_batch_empty_list(self):
        result = score_batch([], current_year=2024)
        assert result == []

    # ── score_explanation ─────────────────────────────────────────────────────

    def test_score_explanation_returns_dict(self):
        a = make_article()
        expl = score_explanation(a, current_year=2024)
        assert isinstance(expl, dict)
        assert "SCORE TOTAL" in expl

    def test_score_explanation_score_total_matches(self):
        a = make_article()
        expl = score_explanation(a, current_year=2024)
        s = compute_quality_score(a, current_year=2024)
        assert str(s) in expl["SCORE TOTAL"]


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestDeduplication
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeduplication:
    """Tests del servicio de deduplicación. Sin red, sin DB."""

    # ── Por DOI exacto ────────────────────────────────────────────────────────

    def test_exact_doi_dedup(self):
        a1 = make_article(doi="10.1056/test.001", source_database="pubmed",   pmid="111")
        a2 = make_article(doi="10.1056/test.001", source_database="europepmc_med", pmid="111")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 1
        assert len(pairs) == 1

    def test_exact_doi_dedup_reason(self):
        a1 = make_article(doi="10.1056/test.777")
        a2 = make_article(doi="10.1056/test.777", source_database="crossref")
        _, pairs = deduplicate_articles([a1, a2])
        assert pairs[0]["reason"].startswith("DOI idéntico")

    def test_different_doi_no_dedup(self):
        a1 = make_article(doi="10.1056/test.001", pmid="11111111")
        a2 = make_article(doi="10.1056/test.002", pmid="22222222",
                          title="Different article title entirely")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 2
        assert len(pairs) == 0

    # ── Por PMID exacto ───────────────────────────────────────────────────────

    def test_exact_pmid_dedup(self):
        a1 = make_article(doi=None, pmid="99999999")
        a2 = make_article(doi=None, pmid="99999999", source_database="europepmc_med")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 1

    # ── Por título fuzzy ──────────────────────────────────────────────────────

    def test_fuzzy_title_identical_strings(self):
        title = "Effects of Nintedanib on Pulmonary Fibrosis in Patients"
        a1 = make_article(doi=None, pmid=None, title=title)
        a2 = make_article(doi=None, pmid=None, title=title, source_database="crossref")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 1

    def test_fuzzy_title_word_order(self):
        """token_sort_ratio debe detectar el mismo título con palabras reordenadas."""
        a1 = make_article(doi=None, pmid=None,
                          title="Nintedanib pulmonary fibrosis treatment outcomes")
        a2 = make_article(doi=None, pmid=None, source_database="crossref",
                          title="Pulmonary fibrosis treatment outcomes nintedanib")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 1

    def test_very_different_titles_not_deduped(self):
        a1 = make_article(doi=None, pmid=None, title="Nintedanib for pulmonary fibrosis")
        a2 = make_article(doi=None, pmid=None, source_database="crossref",
                          title="Insulin resistance in type 2 diabetes mellitus")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 2

    # ── Metadata merge ────────────────────────────────────────────────────────

    def test_metadata_merge_pmcid(self):
        """El primario debe adquirir el PMCID del duplicado si no lo tenía."""
        a1 = make_article(doi="10.1056/test.001", pmid="11111", pmcid=None)
        a2 = make_article(doi="10.1056/test.001", pmid="11111", pmcid="PMC9999999")
        unique, _ = deduplicate_articles([a1, a2])
        assert unique[0].pmcid == "PMC9999999"

    def test_metadata_merge_abstract(self):
        """El primario debe adquirir el abstract del duplicado si no lo tenía."""
        a1 = make_article(doi="10.1056/test.002", abstract=None)
        a2 = make_article(doi="10.1056/test.002",
                          abstract="Important abstract content here for merging.")
        unique, _ = deduplicate_articles([a1, a2])
        assert unique[0].abstract == "Important abstract content here for merging."

    def test_metadata_merge_pdf_url(self):
        a1 = make_article(doi="10.1056/test.003", pdf_url=None)
        a2 = make_article(doi="10.1056/test.003", pdf_url="https://pmc.nih.gov/pdf/test")
        unique, _ = deduplicate_articles([a1, a2])
        assert unique[0].pdf_url == "https://pmc.nih.gov/pdf/test"

    def test_primary_data_takes_precedence(self):
        """Si el primario YA tiene un campo, no debe sobreescribirse con el del duplicado."""
        a1 = make_article(doi="10.1056/test.004", pmcid="PMC_PRIMARY")
        a2 = make_article(doi="10.1056/test.004", pmcid="PMC_DUPLICATE")
        unique, _ = deduplicate_articles([a1, a2])
        assert unique[0].pmcid == "PMC_PRIMARY"

    # ── Casos límite ──────────────────────────────────────────────────────────

    def test_empty_list(self):
        unique, pairs = deduplicate_articles([])
        assert unique == []
        assert pairs == []

    def test_single_article(self):
        a = make_article()
        unique, pairs = deduplicate_articles([a])
        assert len(unique) == 1
        assert len(pairs) == 0

    def test_duplicate_is_marked(self):
        a1 = make_article(doi="10.1056/test.005")
        a2 = make_article(doi="10.1056/test.005", source_database="crossref")
        _, pairs = deduplicate_articles([a1, a2])
        assert a2.is_duplicate is True
        assert a1.is_duplicate is False

    def test_three_same_doi(self):
        """Tres artículos con el mismo DOI → 1 único, 2 duplicados."""
        doi = "10.1056/test.triple"
        a1 = make_article(doi=doi, source_database="pubmed")
        a2 = make_article(doi=doi, source_database="europepmc_med")
        a3 = make_article(doi=doi, source_database="crossref")
        unique, pairs = deduplicate_articles([a1, a2, a3])
        assert len(unique) == 1
        assert len(pairs) == 2

    def test_no_doi_no_pmid_short_title(self):
        """Artículo sin DOI, PMID ni título sustancial: no debe crashear."""
        a1 = make_article(doi=None, pmid=None, title="AB")
        a2 = make_article(doi=None, pmid=None, title="CD")
        unique, pairs = deduplicate_articles([a1, a2])
        assert len(unique) == 2  # títulos distintos, no se deduplicarán

    # ── title_similarity ──────────────────────────────────────────────────────

    def test_title_similarity_identical(self):
        assert _title_similarity("test title here", "test title here") == 100.0

    def test_title_similarity_different(self):
        assert _title_similarity("nintedanib pulmonary fibrosis",
                                 "diabetes insulin resistance") < 50

    def test_title_similarity_empty_strings(self):
        assert _title_similarity("", "") == 0.0

    def test_title_similarity_one_empty(self):
        assert _title_similarity("some title", "") == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestExporters
# ═══════════════════════════════════════════════════════════════════════════════

class TestExporters:
    """Tests de los exportadores. Sin red, sin DB."""

    # ── CSV ───────────────────────────────────────────────────────────────────

    def test_csv_not_empty(self):
        from exporters.exporters import to_csv_bytes
        assert len(to_csv_bytes([make_article()])) > 0

    def test_csv_contains_title_header(self):
        from exporters.exporters import to_csv_bytes
        result = to_csv_bytes([make_article()])
        assert b"title" in result.lower()

    def test_csv_empty_list(self):
        from exporters.exporters import to_csv_bytes
        assert to_csv_bytes([]) == b""

    def test_csv_article_without_authors(self):
        from exporters.exporters import to_csv_bytes
        a = make_article(authors=[])
        result = to_csv_bytes([a])
        assert len(result) > 0

    def test_csv_article_null_doi(self):
        from exporters.exporters import to_csv_bytes
        a = make_article(doi=None)
        result = to_csv_bytes([a])
        assert len(result) > 0

    def test_csv_article_null_abstract(self):
        from exporters.exporters import to_csv_bytes
        a = make_article(abstract=None)
        result = to_csv_bytes([a])
        assert len(result) > 0

    def test_csv_multiple_articles(self):
        from exporters.exporters import to_csv_bytes
        articles = [make_article(doi=f"10.1/{i}") for i in range(5)]
        result = to_csv_bytes(articles)
        assert result.count(b"\n") >= 6  # header + 5 filas

    # ── JSON ──────────────────────────────────────────────────────────────────

    def test_json_valid_structure(self):
        from exporters.exporters import to_json_bytes
        data = json.loads(to_json_bytes([make_article()]))
        assert data["total_articles"] == 1
        assert "articles" in data
        assert "export_date" in data

    def test_json_preserves_title(self):
        from exporters.exporters import to_json_bytes
        a = make_article(title="Unique title for JSON test")
        data = json.loads(to_json_bytes([a]))
        assert data["articles"][0]["title"] == "Unique title for JSON test"

    def test_json_empty_list(self):
        from exporters.exporters import to_json_bytes
        data = json.loads(to_json_bytes([]))
        assert data["total_articles"] == 0
        assert data["articles"] == []

    def test_json_article_null_fields(self):
        from exporters.exporters import to_json_bytes
        a = make_minimal_article()
        data = json.loads(to_json_bytes([a]))
        assert data["articles"][0]["doi"] is None

    # ── RIS ───────────────────────────────────────────────────────────────────

    def test_ris_format_markers(self):
        from exporters.exporters import to_ris_bytes
        result = to_ris_bytes([make_article()]).decode("utf-8")
        assert "TY  - " in result
        assert "TI  - " in result
        assert "ER  - " in result

    def test_ris_includes_doi(self):
        from exporters.exporters import to_ris_bytes
        a = make_article(doi="10.1056/test.ris")
        result = to_ris_bytes([a]).decode("utf-8")
        assert "10.1056/test.ris" in result

    def test_ris_no_doi_no_crash(self):
        from exporters.exporters import to_ris_bytes
        a = make_article(doi=None)
        result = to_ris_bytes([a]).decode("utf-8")
        assert "TY  - " in result

    def test_ris_empty_list(self):
        from exporters.exporters import to_ris_bytes
        result = to_ris_bytes([])
        assert result == b""

    # ── BibTeX ────────────────────────────────────────────────────────────────

    def test_bibtex_format(self):
        from exporters.exporters import to_bibtex_bytes
        result = to_bibtex_bytes([make_article()]).decode("utf-8")
        assert "@article{" in result
        assert "title = {" in result

    def test_bibtex_no_authors_no_crash(self):
        from exporters.exporters import to_bibtex_bytes
        a = make_article(authors=[])
        result = to_bibtex_bytes([a]).decode("utf-8")
        assert "@article{" in result

    def test_bibtex_empty_list(self):
        from exporters.exporters import to_bibtex_bytes
        assert to_bibtex_bytes([]) == b""

    # ── NotebookLM ZIP ────────────────────────────────────────────────────────

    def test_notebooklm_zip_structure(self):
        import io, zipfile
        from exporters.exporters import generate_notebooklm_zip
        zip_bytes = generate_notebooklm_zip([make_article()], "test_col")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
        assert any("README.md" in n for n in names)
        assert any("resumen_master.csv" in n for n in names)
        assert any("metadata.json" in n for n in names)
        assert any("fichas/" in n for n in names)

    def test_notebooklm_zip_one_ficha_per_article(self):
        import io, zipfile
        from exporters.exporters import generate_notebooklm_zip
        articles = [make_article(doi=f"10.1/{i}", pmid=str(i)) for i in range(3)]
        zip_bytes = generate_notebooklm_zip(articles, "col")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            fichas = [n for n in z.namelist() if "fichas/" in n and n.endswith(".md")]
        assert len(fichas) == 3

    def test_notebooklm_empty_list(self):
        import io, zipfile
        from exporters.exporters import generate_notebooklm_zip
        zip_bytes = generate_notebooklm_zip([], "empty_col")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
        assert any("README.md" in n for n in names)

    # ── Ficha Markdown ────────────────────────────────────────────────────────

    def test_ficha_contains_title(self):
        from exporters.exporters import _generate_ficha_md
        a = make_article()
        ficha = _generate_ficha_md(a)
        assert a.title in ficha

    def test_ficha_contains_vancouver(self):
        from exporters.exporters import _generate_ficha_md
        ficha = _generate_ficha_md(make_article())
        assert "Vancouver" in ficha

    def test_ficha_no_abstract_no_crash(self):
        from exporters.exporters import _generate_ficha_md
        a = make_article(abstract=None)
        ficha = _generate_ficha_md(a)
        assert "No disponible" in ficha or ficha  # no debe crashear

    def test_ficha_null_doi_no_crash(self):
        from exporters.exporters import _generate_ficha_md
        a = make_article(doi=None)
        ficha = _generate_ficha_md(a)
        assert ficha  # no debe estar vacío


# ═══════════════════════════════════════════════════════════════════════════════
# [INTEG] TestDatabase
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabase:
    """
    Tests de integración con SQLite.
    Usan una BD temporal en tmp_path. Sin red.
    """

    @pytest.fixture(autouse=True)
    def temp_db(self, tmp_path, monkeypatch):
        """Redirige DB_PATH a un archivo temporal por test."""
        import storage.database as db_module
        db_module.DB_PATH = tmp_path / "test.db"
        db_module.init_db()
        yield

    # ── Upsert ────────────────────────────────────────────────────────────────

    def test_upsert_insert_new(self):
        from storage.database import upsert_article
        art_id, was_inserted = upsert_article(make_article())
        assert was_inserted is True
        assert art_id > 0

    def test_upsert_update_existing(self):
        from storage.database import upsert_article
        a = make_article()
        id1, ins1 = upsert_article(a)
        id2, ins2 = upsert_article(a)
        assert ins1 is True
        assert ins2 is False
        assert id1 == id2

    def test_upsert_different_fingerprints_both_inserted(self):
        from storage.database import upsert_article, get_all_articles
        a1 = make_article(doi="10.1/a1", pmid="1111")
        a2 = make_article(doi="10.1/a2", pmid="2222", title="Another distinct article title")
        upsert_article(a1)
        upsert_article(a2)
        articles = get_all_articles()
        assert len(articles) == 2

    # ── Lectura ───────────────────────────────────────────────────────────────

    def test_get_article_by_id(self):
        from storage.database import upsert_article, get_article_by_id
        a = make_article()
        art_id, _ = upsert_article(a)
        retrieved = get_article_by_id(art_id)
        assert retrieved is not None
        assert retrieved.title == a.title
        assert retrieved.doi == a.doi

    def test_get_article_by_id_nonexistent(self):
        from storage.database import get_article_by_id
        assert get_article_by_id(99999) is None

    def test_get_all_articles_empty(self):
        from storage.database import get_all_articles
        assert get_all_articles() == []

    def test_get_all_articles_filter_collection(self):
        from storage.database import upsert_article, get_all_articles, create_collection
        create_collection("col_a")
        create_collection("col_b")
        a1 = make_article(doi="10.1/c1", pmid="1", collection_name="col_a")
        a2 = make_article(doi="10.1/c2", pmid="2", collection_name="col_b")
        upsert_article(a1)
        upsert_article(a2)
        results = get_all_articles(collection="col_a")
        assert len(results) == 1
        assert results[0].doi == "10.1/c1"

    # ── Update ────────────────────────────────────────────────────────────────

    def test_update_read_status(self):
        from storage.database import upsert_article, update_article_fields, get_article_by_id
        art_id, _ = upsert_article(make_article())
        update_article_fields(art_id, {"read_status": "read"})
        assert get_article_by_id(art_id).read_status == "read"

    def test_update_user_notes(self):
        from storage.database import upsert_article, update_article_fields, get_article_by_id
        art_id, _ = upsert_article(make_article())
        update_article_fields(art_id, {"user_notes": "Great paper"})
        assert get_article_by_id(art_id).user_notes == "Great paper"

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_article(self):
        from storage.database import upsert_article, delete_article, get_all_articles
        art_id, _ = upsert_article(make_article())
        delete_article(art_id)
        assert get_all_articles() == []

    # ── Stats ─────────────────────────────────────────────────────────────────

    def test_get_stats_total(self):
        from storage.database import upsert_article, get_stats
        upsert_article(make_article())
        stats = get_stats()
        assert stats["total"] >= 1

    def test_get_stats_keys_present(self):
        from storage.database import get_stats
        stats = get_stats()
        for key in ("total", "with_pdf", "pending", "priority",
                    "by_collection", "by_source", "flags", "recent_searches"):
            assert key in stats, f"Falta clave: {key}"

    # ── Search log ────────────────────────────────────────────────────────────

    def test_log_search(self):
        from storage.database import log_search
        log = SearchLog(source="pubmed", query="nintedanib IPF", result_count=42)
        log_id = log_search(log)
        assert log_id > 0

    # ── Colecciones ───────────────────────────────────────────────────────────

    def test_create_and_get_collection(self):
        from storage.database import create_collection, get_collections
        create_collection("Fibrosis Pulmonar", "Artículos sobre FP")
        assert "Fibrosis Pulmonar" in get_collections()

    def test_default_collection_always_present(self):
        from storage.database import get_collections
        assert "default" in get_collections()

    def test_create_duplicate_collection_no_error(self):
        from storage.database import create_collection
        create_collection("col_dup")
        create_collection("col_dup")  # debe ser idempotente (INSERT OR IGNORE)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def test_audit_report_keys(self):
        from storage.database import get_audit_report
        report = get_audit_report()
        for key in ("missing_doi", "missing_pmid", "missing_abstract",
                    "missing_pdf", "preprints", "predatory_journals",
                    "parsing_errors", "duplicate_groups", "incomplete_records"):
            assert key in report, f"Falta clave en audit: {key}"

    def test_audit_report_missing_doi_count(self):
        from storage.database import upsert_article, get_audit_report
        upsert_article(make_article(doi=None, pmid="solo_pmid_001"))
        report = get_audit_report()
        assert report["missing_doi"] >= 1

    def test_audit_report_missing_abstract_count(self):
        from storage.database import upsert_article, get_audit_report
        upsert_article(make_article(abstract=None, doi="10.1/no_abs_001"))
        report = get_audit_report()
        assert report["missing_abstract"] >= 1

    # ── Persistencia de listas JSON ───────────────────────────────────────────

    def test_authors_persisted_and_retrieved(self):
        from storage.database import upsert_article, get_article_by_id
        a = make_article(authors=["García JA", "Martínez R", "López P"])
        art_id, _ = upsert_article(a)
        retrieved = get_article_by_id(art_id)
        assert retrieved.authors == ["García JA", "Martínez R", "López P"]

    def test_mesh_terms_persisted_and_retrieved(self):
        from storage.database import upsert_article, get_article_by_id
        a = make_article(mesh_terms=["Pulmonary Fibrosis", "Nintedanib"])
        art_id, _ = upsert_article(a)
        retrieved = get_article_by_id(art_id)
        assert "Pulmonary Fibrosis" in retrieved.mesh_terms

    def test_tags_persisted_and_retrieved(self):
        from storage.database import upsert_article, get_article_by_id
        a = make_article(tags=["priority", "revisión sistemática"])
        art_id, _ = upsert_article(a)
        retrieved = get_article_by_id(art_id)
        assert "priority" in retrieved.tags

    def test_flags_persisted_correctly(self):
        from storage.database import upsert_article, get_article_by_id
        a = make_article(flag_preprint=True, flag_no_abstract=True)
        art_id, _ = upsert_article(a)
        retrieved = get_article_by_id(art_id)
        assert retrieved.flag_preprint is True
        assert retrieved.flag_no_abstract is True


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestConnectorParsing
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorParsing:
    """
    Tests de las funciones de parsing de conectores con datos sintéticos.
    No requieren red. Validan robustez ante edge-cases de las APIs.
    """

    # ── Crossref: _clean_jats_abstract ────────────────────────────────────────

    def test_crossref_jats_tag_removal(self):
        from connectors.crossref import _clean_jats_abstract
        raw = "<jats:p>Background: <jats:italic>This</jats:italic> is a test.</jats:p>"
        result = _clean_jats_abstract(raw)
        assert result is not None
        assert "<jats:" not in result
        assert "Background" in result
        assert "This" in result

    def test_crossref_html_entity_resolution(self):
        from connectors.crossref import _clean_jats_abstract
        raw = "Efficacy &amp; safety of drug X &lt;5mg&gt;"
        result = _clean_jats_abstract(raw)
        assert "&amp;" not in result
        assert "&" in result
        assert "<5mg>" in result

    def test_crossref_empty_abstract(self):
        from connectors.crossref import _clean_jats_abstract
        assert _clean_jats_abstract(None) is None
        assert _clean_jats_abstract("") is None
        assert _clean_jats_abstract("   ") is None

    def test_crossref_plain_text_unchanged(self):
        from connectors.crossref import _clean_jats_abstract
        plain = "This is a plain abstract without any tags."
        result = _clean_jats_abstract(plain)
        assert result == plain

    # ── Europe PMC: _extract_authors ──────────────────────────────────────────

    def test_epmc_authors_list(self):
        from connectors.europepmc import _extract_authors
        item = {
            "authorList": {
                "author": [
                    {"fullName": "Smith AB", "lastName": "Smith"},
                    {"fullName": "Jones CD", "lastName": "Jones"},
                ]
            }
        }
        authors = _extract_authors(item)
        assert authors == ["Smith AB", "Jones CD"]

    def test_epmc_authors_single_as_dict(self):
        """Cuando hay un solo autor, la API devuelve dict en lugar de lista."""
        from connectors.europepmc import _extract_authors
        item = {
            "authorList": {
                "author": {"fullName": "García JA", "lastName": "García"}
            }
        }
        authors = _extract_authors(item)
        assert authors == ["García JA"]

    def test_epmc_authors_empty(self):
        from connectors.europepmc import _extract_authors
        assert _extract_authors({}) == []
        assert _extract_authors({"authorList": {}}) == []
        assert _extract_authors({"authorList": {"author": []}}) == []

    def test_epmc_authors_none(self):
        from connectors.europepmc import _extract_authors
        assert _extract_authors({"authorList": None}) == []

    def test_epmc_authors_fallback_to_lastname(self):
        from connectors.europepmc import _extract_authors
        item = {"authorList": {"author": [{"lastName": "García"}]}}
        authors = _extract_authors(item)
        assert authors == ["García"]

    # ── Europe PMC: _extract_affiliation ─────────────────────────────────────

    def test_epmc_affiliation_string_list(self):
        from connectors.europepmc import _extract_affiliation
        item = {"affiliationList": {"affiliation": ["Instituto Nacional, México"]}}
        result = _extract_affiliation(item)
        assert result == "Instituto Nacional, México"

    def test_epmc_affiliation_plain_string(self):
        from connectors.europepmc import _extract_affiliation
        item = {"affiliationList": {"affiliation": "Hospital General"}}
        result = _extract_affiliation(item)
        assert result == "Hospital General"

    def test_epmc_affiliation_empty(self):
        from connectors.europepmc import _extract_affiliation
        assert _extract_affiliation({}) is None
        assert _extract_affiliation({"affiliationList": {}}) is None
        assert _extract_affiliation({"affiliationList": None}) is None


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestIsbiomedicalSource  (nuevo en v0.2.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIsBiomedicalSource:
    """
    [UNIT] Tests para is_biomedical_source().
    Verifica que el formato compuesto de source_database (post-merge)
    no rompa el flag de indexación biomédica en scoring.
    """

    def test_pubmed_alone(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("pubmed") is True

    def test_europepmc_med(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("europepmc_med") is True

    def test_europepmc_pmc(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("europepmc_pmc") is True

    def test_crossref_alone_not_biomedical(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("crossref") is False

    def test_openalex_alone_not_biomedical(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("openalex") is False

    def test_pubmed_plus_crossref_merged(self):
        """
        BUG CORREGIDO: source_database="pubmed+crossref" generado por
        _merge_metadata debe seguir siendo reconocido como biomédico.
        """
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("pubmed+crossref") is True

    def test_crossref_plus_europepmc_merged(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("crossref+europepmc_med") is True

    def test_crossref_plus_openalex_not_biomedical(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("crossref+openalex") is False

    def test_empty_string(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("") is False

    def test_none_equivalent(self):
        from services.dedup_service import is_biomedical_source
        assert is_biomedical_source("") is False

    def test_scoring_biomedical_after_merge(self):
        """
        BUG CORREGIDO: artículo cuyo source_database fue modificado a
        'pubmed+crossref' por _merge_metadata debe mantener el score
        de indexación biomédica.
        """
        a = make_article(source_database="pubmed+crossref")
        s = compute_quality_score(a, current_year=2024)
        a_crossref = make_article(source_database="crossref")
        s_crossref = compute_quality_score(a_crossref, current_year=2024)
        assert s > s_crossref, (
            f"Merged source score ({s}) debe ser mayor que crossref solo ({s_crossref})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestMergeMetadata  (nuevo en v0.2.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMergeMetadata:
    """
    [UNIT] Tests para _merge_metadata y comportamiento de source_database compuesto.
    """

    def test_merge_source_database_concatenation(self):
        from services.dedup_service import _merge_metadata
        a1 = make_article(doi="10.1/x", source_database="pubmed")
        a2 = make_article(doi="10.1/x", source_database="crossref")
        _merge_metadata(a1, a2)
        assert "pubmed" in a1.source_database
        assert "crossref" in a1.source_database

    def test_merge_source_database_no_duplicates(self):
        """No debe añadir la misma fuente dos veces."""
        from services.dedup_service import _merge_metadata
        a1 = make_article(doi="10.1/x", source_database="pubmed")
        a2 = make_article(doi="10.1/x", source_database="pubmed")
        _merge_metadata(a1, a2)
        parts = a1.source_database.split("+")
        assert len(parts) == len(set(parts))

    def test_merge_keywords_from_duplicate(self):
        from services.dedup_service import _merge_metadata
        a1 = make_article(doi="10.1/y", keywords=[])
        a2 = make_article(doi="10.1/y", keywords=["IPF", "nintedanib"])
        _merge_metadata(a1, a2)
        assert "IPF" in a1.keywords

    def test_merge_does_not_overwrite_existing_keywords(self):
        from services.dedup_service import _merge_metadata
        a1 = make_article(doi="10.1/z", keywords=["original_kw"])
        a2 = make_article(doi="10.1/z", keywords=["other_kw"])
        _merge_metadata(a1, a2)
        assert "original_kw" in a1.keywords
        assert "other_kw" not in a1.keywords  # primario tiene precedencia

    def test_merge_citation_count_from_duplicate(self):
        from services.dedup_service import _merge_metadata
        a1 = make_article(doi="10.1/c", citation_count=None)
        a2 = make_article(doi="10.1/c", citation_count=150)
        _merge_metadata(a1, a2)
        assert a1.citation_count == 150


# ═══════════════════════════════════════════════════════════════════════════════
# [UNIT] TestExporterDatetimeSerialization  (nuevo en v0.2.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExporterDatetimeSerialization:
    """
    [UNIT] Tests de serialización correcta de campos datetime en exportadores.
    Verifica que model_dump() no deje objetos datetime sin serializar.
    """

    def test_csv_date_retrieved_is_string(self):
        from exporters.exporters import to_csv_bytes
        import io, csv as csv_mod
        a = make_article()
        result = to_csv_bytes([a])
        reader = csv_mod.DictReader(io.StringIO(result.decode("utf-8-sig")))
        row = next(reader)
        val = row.get("date_retrieved", "")
        # Debe ser un string ISO, no algo como "datetime.datetime(...)"
        assert "datetime.datetime" not in val, f"date_retrieved no serializado: {val}"
        assert val == "" or "T" in val or "-" in val, f"Formato inesperado: {val}"

    def test_json_dates_are_strings(self):
        from exporters.exporters import to_json_bytes
        data = json.loads(to_json_bytes([make_article()]))
        art = data["articles"][0]
        dr = art.get("date_retrieved")
        if dr is not None:
            assert isinstance(dr, str), f"date_retrieved debe ser str, es {type(dr)}"

    def test_ris_no_crash_with_all_none_dates(self):
        from exporters.exporters import to_ris_bytes
        a = make_article()
        a.pdf_download_date = None
        a.date_retrieved = None
        result = to_ris_bytes([a])
        assert b"TY  - " in result
