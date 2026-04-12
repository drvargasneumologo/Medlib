"""
Página 7: Configuración.
API keys, rutas, parámetros de scoring, fuentes habilitadas.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import os
from pathlib import Path

st.set_page_config(page_title="Settings — MedLib", page_icon="⚙️", layout="wide")

st.title("⚙️ Configuración")
st.caption(
    "Configura API keys, rutas locales y parámetros. "
    "Estas configuraciones se guardan en tu archivo `.env` local, nunca en la nube."
)

# ─── Variables de entorno actuales ────────────────────────────────────────────
ENV_FILE = Path(".env")

def load_env_vars():
    """Lee el .env actual como dict."""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    return env

def save_env_vars(env_dict: dict):
    """Guarda el .env."""
    lines = []
    for k, v in env_dict.items():
        lines.append(f"{k}={v}")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

current_env = load_env_vars()

# ─── APIs y contacto ─────────────────────────────────────────────────────────
st.subheader("Identificación de Aplicación")
st.info(
    "PubMed, Europe PMC y Crossref solicitan un email de contacto en el User-Agent "
    "para acceder al 'Polite Pool' con mejores rate limits. **No se envía a ningún tercero.**"
)

with st.form("settings_form"):
    contact_email = st.text_input(
        "Email de contacto (para User-Agent)",
        value=current_env.get("CONTACT_EMAIL", ""),
        placeholder="tu@email.com",
        help="Se envía en el User-Agent a APIs públicas como buena práctica. Requerido por NCBI."
    )
    app_name = st.text_input(
        "Nombre de la aplicación",
        value=current_env.get("USER_AGENT_APP_NAME", "MedLib"),
        help="Identifica tu aplicación en los logs de las APIs."
    )

    st.subheader("NCBI / PubMed")
    st.markdown(
        "Opcionalmente, [solicita una API key NCBI](https://www.ncbi.nlm.nih.gov/account/) "
        "para obtener 10 req/s en lugar de 3 req/s."
    )
    ncbi_key = st.text_input(
        "NCBI API Key (opcional)",
        value=current_env.get("NCBI_API_KEY", ""),
        type="password",
        help="Obtén una en: https://www.ncbi.nlm.nih.gov/account/"
    )

    st.subheader("Elsevier / Scopus (Opcional)")
    st.warning(
        "⚠️ El módulo Elsevier/Scopus está desactivado en el MVP. "
        "Requiere API key institucional y acceso habilitado. "
        "Configura la key aquí para uso futuro."
    )
    elsevier_key = st.text_input(
        "Elsevier API Key",
        value=current_env.get("ELSEVIER_API_KEY", ""),
        type="password",
        help="API key de Elsevier Developer Portal (requiere cuenta institucional)"
    )

    st.subheader("Acceso Institucional (Módulo Opcional)")
    st.warning(
        "⚠️ El módulo de acceso institucional es experimental. "
        "Solo actívalo si conoces las condiciones de acceso de tu institución."
    )
    col_inst1, col_inst2 = st.columns(2)
    inst_enabled = col_inst1.checkbox(
        "Activar módulo institucional",
        value=current_env.get("INSTITUTION_ENABLED", "false").lower() == "true"
    )
    inst_name = col_inst2.text_input(
        "Nombre de institución",
        value=current_env.get("INSTITUTION_NAME", "")
    )

    st.subheader("Parámetros de Scoring")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        w_doi    = st.slider("Peso: DOI presente",            0, 20, int(current_env.get("SCORE_W_DOI", 10)))
        w_abs    = st.slider("Peso: Abstract presente",       0, 20, int(current_env.get("SCORE_W_ABSTRACT", 12)))
        w_pmid   = st.slider("Peso: PMID presente",           0, 20, int(current_env.get("SCORE_W_PMID", 8)))
        w_bio    = st.slider("Peso: Indexación biomédica",    0, 20, int(current_env.get("SCORE_W_BIOMEDICAL", 10)))
    with col_s2:
        w_year   = st.slider("Peso: Recencia",                0, 20, int(current_env.get("SCORE_W_YEAR", 8)))
        w_ft     = st.slider("Peso: Texto completo",          0, 20, int(current_env.get("SCORE_W_FULLTEXT", 8)))
        w_evid   = st.slider("Peso: Tipo de evidencia alta",  0, 20, int(current_env.get("SCORE_W_EVIDENCE", 10)))
        w_oa     = st.slider("Peso: Acceso abierto",          0, 20, int(current_env.get("SCORE_W_OA", 5)))

    st.subheader("Base de Datos")
    db_path = st.text_input(
        "Ruta de la base de datos SQLite",
        value=current_env.get("DB_PATH", "data/medlib.db"),
        help="Ruta relativa al directorio de trabajo"
    )

    submitted = st.form_submit_button("💾 Guardar configuración", type="primary")

if submitted:
    new_env = {
        "CONTACT_EMAIL": contact_email,
        "USER_AGENT_APP_NAME": app_name,
        "NCBI_API_KEY": ncbi_key,
        "ELSEVIER_API_KEY": elsevier_key,
        "INSTITUTION_ENABLED": str(inst_enabled).lower(),
        "INSTITUTION_NAME": inst_name,
        "SCORE_W_DOI": str(w_doi),
        "SCORE_W_ABSTRACT": str(w_abs),
        "SCORE_W_PMID": str(w_pmid),
        "SCORE_W_BIOMEDICAL": str(w_bio),
        "SCORE_W_YEAR": str(w_year),
        "SCORE_W_FULLTEXT": str(w_ft),
        "SCORE_W_EVIDENCE": str(w_evid),
        "SCORE_W_OA": str(w_oa),
        "DB_PATH": db_path,
    }
    # No guardar valores vacíos sensibles
    if not new_env["NCBI_API_KEY"]:
        new_env.pop("NCBI_API_KEY")
    if not new_env["ELSEVIER_API_KEY"]:
        new_env.pop("ELSEVIER_API_KEY")

    save_env_vars(new_env)

    # Recargar variables de entorno en la sesión actual
    for k, v in new_env.items():
        os.environ[k] = v

    st.success(
        "✅ Configuración guardada en `.env`. "
        "Reinicia la aplicación para que todos los cambios surtan efecto."
    )

st.markdown("---")

# ─── Estado del sistema ───────────────────────────────────────────────────────
st.subheader("Estado del Sistema")

col1, col2, col3 = st.columns(3)

db_file = Path("data/medlib.db")
with col1:
    if db_file.exists():
        size_kb = db_file.stat().st_size / 1024
        st.success(f"✅ Base de datos: {size_kb:.1f} KB")
    else:
        st.error("❌ Base de datos no encontrada")

with col2:
    try:
        import requests
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi", timeout=5)
        if r.status_code == 200:
            st.success("✅ PubMed API: accesible")
        else:
            st.warning(f"⚠️ PubMed API: status {r.status_code}")
    except Exception:
        st.error("❌ PubMed API: no accesible (verifica conexión)")

with col3:
    try:
        import requests
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&pageSize=1&format=json", timeout=5)
        if r.status_code == 200:
            st.success("✅ Europe PMC API: accesible")
        else:
            st.warning(f"⚠️ Europe PMC API: status {r.status_code}")
    except Exception:
        st.error("❌ Europe PMC API: no accesible")

st.markdown("---")
st.subheader("Acerca de MedLib")
st.markdown("""
**MedLib v0.1.0** — Biblioteca Personal de Literatura Científica Biomédica

- 🔬 Fuentes: PubMed, Europe PMC, Crossref, OpenAlex
- 🗄️ Base de datos: SQLite (local)
- 📤 Exportaciones: CSV, JSON, RIS, BibTeX, NotebookLM
- 🔑 APIs oficiales públicas únicamente
- 🔒 Sin envío de datos a terceros
- 📄 Licencia: Uso personal/educativo

**No intenta eludir paywalls, restricciones de licencia ni autenticaciones protegidas.**
""")
