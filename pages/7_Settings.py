"""
Página 7: Configuración completa.
Incluye: APIs, credenciales institucionales, acceso PDF, Google Scholar,
parámetros de scoring y estado del sistema.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import streamlit as st

st.set_page_config(page_title="Settings — MedLib", page_icon="⚙️", layout="wide")

st.title("⚙️ Configuración")
st.caption(
    "Todas las configuraciones se guardan en `.env` local. "
    "**Nunca se envían a ningún servidor externo ni a Anthropic.**"
)

ENV_FILE = Path(".env")

def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def save_env(env_dict: dict):
    lines = ["# MedLib — Configuración local", "# Generado automáticamente. No subir a Git.", ""]
    for k, v in env_dict.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

env = load_env()

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: IDENTIDAD Y APIS PÚBLICAS
# ═══════════════════════════════════════════════════════════════════════════════
st.header("1. APIs Públicas")
st.info(
    "PubMed, Europe PMC y Crossref solicitan un email de contacto en el "
    "User-Agent HTTP para acceder al 'Polite Pool' (mejor rate limit). "
    "**No se envía a terceros.**"
)

with st.form("form_apis"):
    c1, c2 = st.columns(2)
    contact_email = c1.text_input(
        "📧 Email de contacto",
        value=env.get("CONTACT_EMAIL", ""),
        placeholder="tu@email.com",
        help="Requerido por PubMed/NCBI como buena práctica de API.",
    )
    app_name = c2.text_input(
        "Nombre de la aplicación",
        value=env.get("USER_AGENT_APP_NAME", "MedLib"),
    )

    st.subheader("NCBI / PubMed API Key")
    c3, c4 = st.columns([2, 2])
    ncbi_key = c3.text_input(
        "NCBI API Key",
        value=env.get("NCBI_API_KEY", ""),
        type="password",
        help="Sin key: 3 req/s. Con key: 10 req/s. Gratis en: ncbi.nlm.nih.gov/account/",
    )
    c4.markdown(
        "**¿Cómo obtenerla?**\n\n"
        "1. Ve a [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/)\n"
        "2. Inicia sesión o crea cuenta gratuita\n"
        "3. Ve a Account Settings → API Key Management\n"
        "4. Genera y copia la key aquí"
    )

    st.subheader("Elsevier / Scopus API Key")
    c5, c6 = st.columns([2, 2])
    elsevier_key = c5.text_input(
        "Elsevier API Key",
        value=env.get("ELSEVIER_API_KEY", ""),
        type="password",
        help="Requiere cuenta institucional con suscripción Scopus.",
    )
    c6.markdown(
        "**¿Cómo obtenerla?**\n\n"
        "1. Ve a [dev.elsevier.com](https://dev.elsevier.com/)\n"
        "2. Crea cuenta con email institucional\n"
        "3. Crea aplicación → copia API Key\n"
        "4. Tu institución debe tener suscripción activa"
    )

    submit_apis = st.form_submit_button("💾 Guardar APIs públicas", type="primary")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: ACCESO INSTITUCIONAL Y PDFs
# ═══════════════════════════════════════════════════════════════════════════════
st.header("2. Acceso Institucional a PDFs")

with st.expander("ℹ️ ¿Cómo funciona el acceso institucional?", expanded=False):
    st.markdown("""
    MedLib puede intentar descargar PDFs restringidos usando tu acceso institucional
    por tres métodos (en orden de preferencia):

    **Método A — EZproxy** (más común en universidades mexicanas e internacionales):
    - Tu biblioteca tiene un servidor EZproxy que actúa como intermediario.
    - Cuando MedLib detecta un artículo con acceso restringido, reescribe la URL
      a través del EZproxy de tu institución.
    - **Requisito:** conocer la URL base del EZproxy de tu institución.
    - Ejemplos: UNAM (`https://login.bidi.unam.mx/login?url=`),
      IMSS, ISSSTE, hospitales con biblioteca digital.

    **Método B — Proxy HTTP corporativo:**
    - Si tu institución tiene un proxy HTTP/HTTPS configurado en la red,
      MedLib lo usará para las descargas.
    - Funciona solo si estás en la red institucional o por VPN.

    **Método C — Cookie de sesión:**
    - Inicias sesión manualmente en el sitio del editor desde tu navegador.
    - Copias la cookie de sesión y la pegas aquí.
    - **Nota:** Las cookies expiran; deberás renovarlas periódicamente.

    **⚠️ Importante:** MedLib nunca almacena contraseñas. Solo usa los
    parámetros técnicos que tú configures. Asegúrate de tener acceso
    legítimo a los recursos que intentas descargar.
    """)

with st.form("form_institutional"):
    st.subheader("Configuración General")
    c1, c2 = st.columns(2)
    inst_enabled = c1.checkbox(
        "✅ Activar acceso institucional",
        value=env.get("INSTITUTION_ENABLED", "false").lower() == "true",
        help="Habilita los intentos de descarga via EZproxy, proxy HTTP o cookies.",
    )
    inst_name = c2.text_input(
        "Nombre de la institución",
        value=env.get("INSTITUTION_NAME", ""),
        placeholder="UNAM, IMSS, Hospital General...",
    )

    st.subheader("Método A — EZproxy")
    c3, c4 = st.columns([2, 2])
    ezproxy_url = c3.text_input(
        "URL base del EZproxy institucional",
        value=env.get("EZPROXY_BASE_URL", ""),
        placeholder="https://login.biblioteca.miinstitución.mx/login?url=",
        help="La URL del artículo original se añade al final de este prefijo.",
    )
    c4.markdown(
        "**¿Cómo encontrar la URL de tu EZproxy?**\n\n"
        "1. Busca en la web de tu biblioteca: 'acceso remoto' o 'proxy'\n"
        "2. La URL suele terminar en `?url=` o `?qurl=`\n"
        "3. Ejemplo UNAM: `https://login.bidi.unam.mx/login?url=`\n"
        "4. Ejemplo genérico: `https://ezproxy.miuinversidad.edu/login?url=`"
    )

    st.subheader("Método B — Proxy HTTP")
    c5, c6 = st.columns(2)
    proxy_http = c5.text_input(
        "Proxy HTTP",
        value=env.get("INSTITUTION_PROXY_HTTP", ""),
        placeholder="http://proxy.institucion.edu:3128",
    )
    proxy_https = c6.text_input(
        "Proxy HTTPS",
        value=env.get("INSTITUTION_PROXY_HTTPS", ""),
        placeholder="http://proxy.institucion.edu:3128",
    )

    st.subheader("Método C — Cookie de Sesión")
    st.warning(
        "⚠️ Las cookies expiran periódicamente. Si la descarga falla, "
        "renueva tu sesión en el sitio del editor y actualiza la cookie aquí."
    )
    c7, c8 = st.columns(2)
    cookie_name = c7.text_input(
        "Nombre de la cookie",
        value=env.get("INSTITUTION_COOKIE_NAME", ""),
        placeholder="sessionid, ShibSession, etc.",
        help="Nombre técnico de la cookie de sesión del editor.",
    )
    cookie_value = c8.text_input(
        "Valor de la cookie",
        value=env.get("INSTITUTION_COOKIE_VALUE", ""),
        type="password",
        placeholder="abc123xyz...",
        help="Valor de la cookie. Se obtiene desde las DevTools del navegador.",
    )

    with st.expander("📋 Cómo obtener una cookie de sesión", expanded=False):
        st.markdown("""
        1. Abre Chrome o Firefox y navega al sitio del editor (ej. ScienceDirect, Wiley, Springer).
        2. Inicia sesión con tus credenciales institucionales o SSO.
        3. Abre las **Developer Tools** (`F12`).
        4. Ve a la pestaña **Application** (Chrome) o **Storage** (Firefox).
        5. En el panel izquierdo, expande **Cookies** → selecciona el dominio del editor.
        6. Busca la cookie de sesión principal (suele llamarse `sessionid`, `ShibSession`, `JSESSIONID`, etc.)
        7. Copia el **Name** y el **Value** y pégalos aquí.
        8. Las cookies típicamente duran 1-7 días. Cuando expiren, repite el proceso.
        """)

    submit_inst = st.form_submit_button("💾 Guardar acceso institucional", type="primary")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: GOOGLE SCHOLAR
# ═══════════════════════════════════════════════════════════════════════════════
st.header("3. Google Scholar (Módulo Experimental)")

with st.expander("⚠️ Advertencias importantes antes de activar", expanded=True):
    st.error("""
    **Google Scholar NO tiene API oficial.**

    El módulo usa la librería `scholarly` que hace scraping del HTML público
    de Scholar. Esto implica:

    - **Puede violar** los Términos de Servicio de Google si se usa de forma masiva.
    - **Google bloquea IPs** que hacen demasiadas peticiones (CAPTCHA, HTTP 429).
    - **Los metadatos son incompletos**: sin PMID, sin abstract completo, fechas aproximadas.
    - **No es confiable** para uso clínico formal — úsalo solo como complemento.
    - **Máximo 10-15 resultados** por búsqueda para evitar bloqueos.

    **Uso recomendado:** encontrar citas/citaciones no indexadas en PubMed,
    artículos de revistas regionales latinoamericanas, o tesis doctorales.
    """)

with st.form("form_scholar"):
    c1, c2 = st.columns(2)
    scholar_enabled = c1.checkbox(
        "Activar Google Scholar",
        value=env.get("SCHOLAR_ENABLED", "false").lower() == "true",
        help="Requiere: pip install scholarly",
    )
    scholar_max = c2.slider(
        "Máximo de resultados por búsqueda",
        min_value=5, max_value=20, value=int(env.get("SCHOLAR_MAX_RESULTS", "10")),
        help="Máximo recomendado: 15. Más de 20 incrementa el riesgo de bloqueo.",
    )
    scholar_delay = c2.slider(
        "Pausa entre peticiones (segundos)",
        min_value=1, max_value=10, value=int(env.get("SCHOLAR_DELAY_SECONDS", "3")),
        help="Más pausa = menos riesgo de bloqueo. Mínimo recomendado: 3s.",
    )

    # Verificar si scholarly está instalado
    try:
        import scholarly  # noqa: F401
        st.success("✅ `scholarly` está instalado y disponible.")
    except ImportError:
        st.warning(
            "📦 `scholarly` no está instalado. Para habilitarlo:\n\n"
            "```\npip install scholarly\n```\n\n"
            "Ejecuta este comando en el entorno virtual del proyecto."
        )

    submit_scholar = st.form_submit_button("💾 Guardar configuración Scholar")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: UNPAYWALL
# ═══════════════════════════════════════════════════════════════════════════════
st.header("4. Unpaywall — Búsqueda de PDFs Legales")
st.info(
    "**Unpaywall** encuentra versiones legales en acceso abierto de artículos "
    "con DOI. Gratuito, sin API key, requiere solo tu email. "
    "Cubre ~50 millones de artículos."
)

with st.form("form_unpaywall"):
    c1, c2 = st.columns(2)
    unp_enabled = c1.checkbox(
        "✅ Activar enriquecimiento con Unpaywall",
        value=env.get("UNPAYWALL_ENABLED", "true").lower() == "true",
        help="Al guardar artículos con DOI, consulta Unpaywall para encontrar PDFs OA.",
    )
    unp_auto = c2.checkbox(
        "Consultar automáticamente al guardar artículos",
        value=env.get("UNPAYWALL_AUTO_ENRICH", "true").lower() == "true",
    )
    submit_unp = st.form_submit_button("💾 Guardar Unpaywall")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: SCORING
# ═══════════════════════════════════════════════════════════════════════════════
st.header("5. Parámetros de Score de Calidad")
st.caption(
    "Ajusta la importancia de cada criterio en el score (0-20 pts). "
    "Los pesos se normalizan automáticamente a escala 0-100."
)

with st.form("form_scoring"):
    c1, c2 = st.columns(2)
    with c1:
        w_doi  = st.slider("DOI presente",            0, 20, int(env.get("SCORE_W_DOI", 10)))
        w_abs  = st.slider("Abstract presente",       0, 20, int(env.get("SCORE_W_ABSTRACT", 12)))
        w_pmid = st.slider("PMID presente",           0, 20, int(env.get("SCORE_W_PMID", 8)))
        w_bio  = st.slider("Indexación biomédica",    0, 20, int(env.get("SCORE_W_BIOMEDICAL", 10)))
    with c2:
        w_year = st.slider("Recencia (últimos 10 años)", 0, 20, int(env.get("SCORE_W_YEAR", 8)))
        w_ft   = st.slider("Texto completo disponible",  0, 20, int(env.get("SCORE_W_FULLTEXT", 8)))
        w_evid = st.slider("Tipo de evidencia alta",     0, 20, int(env.get("SCORE_W_EVIDENCE", 10)))
        w_oa   = st.slider("Acceso abierto",             0, 20, int(env.get("SCORE_W_OA", 5)))

    total_pts = w_doi + w_abs + w_pmid + w_bio + w_year + w_ft + w_evid + w_oa
    st.caption(f"Suma de pesos activos: **{total_pts}** pts (se normalizan a 100)")
    submit_scoring = st.form_submit_button("💾 Guardar parámetros de scoring")

# ═══════════════════════════════════════════════════════════════════════════════
# PROCESAR FORMULARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def _save_and_reload(updates: dict):
    env.update(updates)
    # Limpiar valores vacíos sensibles
    for sensitive in ("NCBI_API_KEY", "ELSEVIER_API_KEY", "INSTITUTION_COOKIE_VALUE"):
        if not env.get(sensitive):
            env.pop(sensitive, None)
    save_env(env)
    for k, v in env.items():
        os.environ[k] = v

if submit_apis:
    _save_and_reload({
        "CONTACT_EMAIL": contact_email,
        "USER_AGENT_APP_NAME": app_name,
        "NCBI_API_KEY": ncbi_key,
        "ELSEVIER_API_KEY": elsevier_key,
    })
    st.success("✅ APIs públicas guardadas.")

if submit_inst:
    _save_and_reload({
        "INSTITUTION_ENABLED":     str(inst_enabled).lower(),
        "INSTITUTION_NAME":        inst_name,
        "EZPROXY_BASE_URL":        ezproxy_url,
        "INSTITUTION_PROXY_HTTP":  proxy_http,
        "INSTITUTION_PROXY_HTTPS": proxy_https,
        "INSTITUTION_COOKIE_NAME": cookie_name,
        "INSTITUTION_COOKIE_VALUE":cookie_value,
    })
    st.success("✅ Acceso institucional guardado.")
    if inst_enabled and not any([ezproxy_url, proxy_http, cookie_name]):
        st.warning(
            "⚠️ Acceso institucional activado pero sin ningún método configurado. "
            "Configura al menos EZproxy, Proxy HTTP o Cookie de sesión."
        )

if submit_scholar:
    _save_and_reload({
        "SCHOLAR_ENABLED":        str(scholar_enabled).lower(),
        "SCHOLAR_MAX_RESULTS":    str(scholar_max),
        "SCHOLAR_DELAY_SECONDS":  str(scholar_delay),
    })
    st.success("✅ Configuración Scholar guardada.")

if submit_unp:
    _save_and_reload({
        "UNPAYWALL_ENABLED":      str(unp_enabled).lower(),
        "UNPAYWALL_AUTO_ENRICH":  str(unp_auto).lower(),
    })
    st.success("✅ Configuración Unpaywall guardada.")

if submit_scoring:
    _save_and_reload({
        "SCORE_W_DOI":        str(w_doi),
        "SCORE_W_ABSTRACT":   str(w_abs),
        "SCORE_W_PMID":       str(w_pmid),
        "SCORE_W_BIOMEDICAL": str(w_bio),
        "SCORE_W_YEAR":       str(w_year),
        "SCORE_W_FULLTEXT":   str(w_ft),
        "SCORE_W_EVIDENCE":   str(w_evid),
        "SCORE_W_OA":         str(w_oa),
    })
    st.success("✅ Parámetros de scoring guardados.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6: ESTADO DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════════════════
st.header("6. Estado del Sistema")

col1, col2, col3, col4 = st.columns(4)

db_file = Path("data/medlib.db")
with col1:
    if db_file.exists():
        size_kb = db_file.stat().st_size / 1024
        st.success(f"✅ SQLite: {size_kb:.1f} KB")
    else:
        st.error("❌ Base de datos no encontrada")

with col2:
    try:
        import requests
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi", timeout=5)
        st.success("✅ PubMed API: OK") if r.status_code == 200 else st.warning(f"⚠️ PubMed: {r.status_code}")
    except Exception:
        st.error("❌ PubMed API: sin acceso")

with col3:
    try:
        import requests
        r = requests.get("https://api.unpaywall.org/v2/10.1056/NEJMoa1809349?email=test@test.com", timeout=5)
        st.success("✅ Unpaywall: OK") if r.status_code == 200 else st.warning(f"⚠️ Unpaywall: {r.status_code}")
    except Exception:
        st.error("❌ Unpaywall: sin acceso")

with col4:
    try:
        import scholarly  # noqa: F401
        st.success("✅ scholarly: instalado")
    except ImportError:
        st.warning("⚠️ scholarly: no instalado")

# Verificar configuración institucional
if env.get("INSTITUTION_ENABLED", "false").lower() == "true":
    from connectors.pdf_access import InstitutionalAccessConfig
    cfg = InstitutionalAccessConfig()
    st.info(f"🏛️ Acceso institucional: {cfg}")

st.markdown("---")
st.subheader("Acerca de MedLib")
st.markdown("""
**MedLib v0.3.0** — Biblioteca Personal de Literatura Científica Biomédica

| Componente | Estado |
|---|---|
| PubMed (E-utilities) | ✅ Activo |
| Europe PMC | ✅ Activo |
| Crossref | ✅ Activo |
| OpenAlex | ✅ Activo |
| Unpaywall (PDFs OA) | ✅ Activo si CONTACT_EMAIL configurado |
| Google Scholar | ⚠️ Experimental, desactivado por defecto |
| Scopus/Elsevier | ⚠️ Solo con API key institucional |
| Acceso Institucional | ⚙️ Configurable en esta página |

*No intenta eludir paywalls, DRM ni autenticaciones protegidas.*
""")
