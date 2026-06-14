# 🔬 MedLib — Biblioteca Personal de Literatura Biomédica

**v0.2.0** | Python + Streamlit | PubMed · Europe PMC · Crossref · OpenAlex

MedLib es una aplicación web local que permite **buscar, normalizar, deduplicar,
puntuar y exportar literatura científica biomédica** desde APIs oficiales públicas,
con almacenamiento local en SQLite y exportación a NotebookLM.

---

## Estado de Validación

Esta tabla es honesta sobre lo que está validado y lo que no.

| Componente | Validación | Tipo |
|---|---|---|
| Modelos Pydantic v2 (normalización, fingerprint, Vancouver) | ✅ Tests unitarios offline | UNIT |
| Scoring: invariantes semánticas, umbrales, tipos evidencia | ✅ Tests unitarios offline | UNIT |
| Deduplicación: DOI, PMID, fuzzy, merge | ✅ Tests unitarios offline | UNIT |
| Exportadores: CSV, JSON, RIS, BibTeX, ZIP NotebookLM | ✅ Tests unitarios offline | UNIT |
| Base de datos SQLite: CRUD, upsert, stats, logs | ✅ Tests integración con BD temporal | INTEG |
| Parsing de conectores (JATS, autor único EPMC) | ✅ Tests unitarios con datos sintéticos | UNIT |
| Comportamiento real contra API PubMed | ❌ Pendiente validación en vivo | PENDING |
| Comportamiento real contra API Europe PMC | ❌ Pendiente validación en vivo | PENDING |
| Comportamiento real contra API Crossref | ❌ Pendiente validación en vivo | PENDING |
| Comportamiento real contra API OpenAlex | ❌ Pendiente validación en vivo | PENDING |
| Interfaz Streamlit (funcionalidad visual) | ❌ No testeada con pytest | PENDING |
| Rate limiting y reintentos (tenacity) | ❌ No testeado | PENDING |
| Migración de esquema SQLite entre versiones | ❌ No implementada | N/A |

---

## Known Limitations

### Conectores (crítico, pendiente validación en vivo)

**PubMed (E-utilities)**
- El parsing de XML asume la estructura documentada por NCBI. Cambios en el
  esquema de respuesta romperían el parser silenciosamente.
- Artículos con `ArticleTitle` que contienen sub-elementos XML (`<i>`, `<sub>`)
  se manejan con `itertext()`, pero no se ha validado con casos reales edge-cases.
- Sin API key: 3 req/s; con API key: 10 req/s. El código implementa el delay pero
  no se ha validado el comportamiento bajo carga real.

**Europe PMC**
- Cuando un artículo tiene un solo autor, la API puede devolver `dict` en lugar
  de `list` en el campo `authorList.author`. Esto está manejado con `isinstance()`,
  pero solo validado con datos sintéticos, no con respuestas reales de la API.
- El campo `affiliationList` tiene estructura inconsistente entre versiones de la
  API. El parser es defensivo pero puede producir `None` en casos no cubiertos.
- Los abstracts en formato JATS XML se limpian con regex básico; entidades HTML
  poco comunes pueden no resolverse correctamente.

**Crossref**
- No provee estado OA directamente. Para acceso abierto verificado se necesitaría
  integrar Unpaywall API (no implementado en MVP).
- Los abstracts en formato JATS XML se limpian con `html.unescape()` + regex.
  Casos con entidades XML numéricas (`&#x...;`) pueden producir artefactos.

**OpenAlex**
- La reconstrucción del abstract desde `abstract_inverted_index` es correcta
  algorítmicamente pero no se ha validado con abstracts de más de 500 palabras.
- El campo `keywords` tiene estructura inconsistente entre versiones de la API.

### Deduplicación

- El threshold fuzzy (92) es conservador. Puede producir falsos negativos
  (artículos duplicados no detectados) si los títulos difieren significativamente
  por fuente. Ajustable en código.
- La fusión de metadatos (`_merge_metadata`) prioriza el artículo primario.
  Si el primario tiene datos erróneos, los datos correctos del duplicado se
  pierden silenciosamente. No hay logging de conflictos de merge.

### Scoring

- Los pesos por defecto son provisionales (juicio experto). No están validados
  contra estudios de evaluación bibliométrica.
- `MIN_ABSTRACT_LENGTH = 20` es permisivo. Un abstract de 20 caracteres no
  aporta información clínica útil, pero suma puntos.
- El score normaliza sobre la suma de pesos activos, no sobre 100 fijo. Cambiar
  los pesos afecta el denominador, haciendo que scores con distintos sets de
  pesos no sean comparables entre sí.

### Base de Datos

- No hay migración de esquema entre versiones. Si el modelo `Article` cambia,
  la BD existente puede quedar incompatible. Solución manual: borrar `data/medlib.db`.
- Sin índice de texto completo (FTS5). La búsqueda por `search_text` usa `LIKE`,
  que no escala bien con más de ~50,000 artículos.
- Sin mecanismo de backup automatizado.

### Interfaz Streamlit

- La función `_show_article_detail` en `pages/2_Search.py` se define después de
  su llamada en el flujo del script. Funciona en Streamlit (que no sigue el orden
  de ejecución Python estándar), pero es frágil ante refactorizaciones.
- No se ha testeado la UI con ningún framework de testing de Streamlit.

### PDFs y acceso

- Solo se obtienen enlaces a PDFs cuando la fuente los provee en los metadatos.
- No se implementa descarga automática de PDFs. No se intenta bypass de paywalls.
- Los endpoints de PMC PDF (`/pmc/articles/{PMCID}/pdf/`) son válidos solo para
  artículos en PMC Central con texto completo disponible.

---

## Instalación y Ejecución

```bash
# 1. Clonar/descargar el proyecto
cd medlib

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env: añadir tu email en CONTACT_EMAIL

# 5. Ejecutar
streamlit run app.py
```

La app se abre en `http://localhost:8501`.

---

## Ejecutar Tests

```bash
# Todos los tests offline (unitarios + integración SQLite)
pytest tests/ -v

# Solo unitarios (sin BD)
pytest tests/ -v -k "not TestDatabase"

# Con traceback resumido
pytest tests/ -v --tb=short

# Ver clasificación de tests
pytest tests/ -v --collect-only
```

**Tests offline:** 134 tests definidos.  
**Tests que requieren red:** 0 en esta suite.  
**Tests de interfaz Streamlit:** 0 (no implementados en MVP).

---

## Estructura del Proyecto

```
medlib/
├── app.py                      # Entry point Streamlit
├── pages/
│   ├── 1_Dashboard.py          # Resumen estadísticas
│   ├── 2_Search.py             # Búsqueda avanzada
│   ├── 3_Library.py            # Gestión biblioteca
│   ├── 4_Duplicates.py         # Revisión duplicados
│   ├── 5_Exports.py            # Exportaciones
│   ├── 6_Audit.py              # Auditoría calidad
│   └── 7_Settings.py           # Configuración
├── connectors/
│   ├── pubmed.py               # NCBI E-utilities (XML)
│   ├── europepmc.py            # Europe PMC REST API (JSON)
│   ├── crossref.py             # Crossref REST API (JSON)
│   └── openalex.py             # OpenAlex API (JSON)
├── models/
│   └── article.py              # Esquema Pydantic v2 unificado
├── services/
│   ├── search_service.py       # Orquestador de búsqueda
│   ├── dedup_service.py        # Deduplicación con rapidfuzz
│   └── scoring_service.py      # Score de calidad configurable
├── storage/
│   └── database.py             # Capa SQLite con Pydantic v2
├── exporters/
│   └── exporters.py            # CSV, JSON, RIS, BibTeX, NotebookLM
├── tests/
│   └── test_medlib.py          # 134 tests (UNIT + INTEG)
├── data/                       # BD SQLite y logs (gitignored)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Fuentes y APIs

| Fuente | API | Auth | Validado en vivo |
|---|---|---|---|
| PubMed | NCBI E-utilities | Opcional (API key) | ❌ Pendiente |
| Europe PMC | REST pública | No requerida | ❌ Pendiente |
| Crossref | REST pública (Polite Pool) | No requerida | ❌ Pendiente |
| OpenAlex | REST pública | No requerida | ❌ Pendiente |
| Google Scholar | No implementado | — | N/A (viola ToS) |
| Scopus/Elsevier | Módulo experimental desactivado | API key inst. | N/A |

---

## Cambios v0.1.0 → v0.2.0

| Cambio | Archivo |
|---|---|
| `MIN_ABSTRACT_LENGTH`: 50 → 20 (corregía test fallido) | `scoring_service.py` |
| `Article.__fields__` → `Article.model_fields` (Pydantic v2 canónico) | `database.py` |
| `ORDER BY quality_score DESC NULLS LAST` (SQLite 3.30+) | `database.py` |
| `html.unescape()` para entidades HTML en abstracts Crossref | `crossref.py` |
| `isinstance(author_list, dict)` para autor único EPMC | `europepmc.py` |
| `_clean_jats_abstract()` refactorizada como función pública | `crossref.py` |
| `_extract_authors()` y `_extract_affiliation()` como funciones públicas | `europepmc.py` |
| Eliminado `__import__()` inline en Audit page | `pages/6_Audit.py` |
| Tests: 42 → 134 (añadidos edge-cases, null fields, invariantes) | `tests/test_medlib.py` |
| `test_custom_weights` reescrito con invariante semántica robusta | `tests/test_medlib.py` |
| `test_year_very_old` nuevo: año >10 años == año None | `tests/test_medlib.py` |
| `TestConnectorParsing`: 14 nuevos tests de parsing con datos sintéticos | `tests/test_medlib.py` |
| Sección `Known Limitations` en README | `README.md` |
| Tabla de estado de validación en README | `README.md` |

---

## Seguridad

- Credenciales: solo en `.env` (excluido en `.gitignore`). Nunca en código.
- APIs: solo llamadas de lectura a APIs públicas.
- No se implementa bypass de paywalls, autenticaciones complejas ni scraping.
