import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from features import cargar  # noqa: E402

import prediccion  # noqa: E402

API_URL = (os.environ.get("API_URL") or "").rstrip("/") or None

# Paleta tomada del mockup v2: azul institucional, rojo de alerta, ámbar.
AZUL = "#1F3B63"
AZUL_MEDIO = "#3B6FB6"
AZUL_CLARO = "#A9C1E3"
ROJO = "#C0392B"
AMBAR = "#D98E04"
VERDE = "#2E7D5B"
GRIS = "#6B7280"
NIVELES = {"alta": ROJO, "media": AMBAR, "baja": VERDE}

TIPOS = {
    "Cualquiera": ("y", "adición en tiempo o en valor"),
    "En tiempo": ("y_tiempo", "adición en tiempo"),
    "En valor": ("y_valor", "adición en valor"),
}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
BINS_PLAZO = [0, 30, 90, 180, 365, 730, np.inf]
ETIQ_PLAZO = ["≤30", "31–90", "91–180", "181–365", "366–730", ">730"]

pio.templates["tablero"] = go.layout.Template(
    layout=dict(
        font=dict(family="Source Sans Pro, Segoe UI, sans-serif", size=13,
                  color="#1F2937"),
        colorway=[AZUL_MEDIO, ROJO, AMBAR, VERDE, GRIS],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="#E5E7EB", zeroline=False),
        yaxis=dict(gridcolor="#E5E7EB", zeroline=False),
        hoverlabel=dict(font_size=12),
        separators=",.",
    ))
pio.templates.default = "tablero"


# --------------------------------------------------------------------------
# Formato en español
# --------------------------------------------------------------------------
def pct(x, dec=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{100 * x:.{dec}f} %".replace(".", ",")


def entero(x):
    return f"{x:,.0f}".replace(",", ".")


def pesos(x):
    """Pesos en la escala más legible: billones, miles de millones o millones."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    for escala, nombre in [(1e12, "billones"), (1e9, "mil millones"),
                           (1e6, "millones")]:
        if abs(x) >= escala:
            return f"$ {x / escala:,.1f} {nombre}".replace(",", "_") \
                .replace(".", ",").replace("_", ".")
    return f"$ {entero(x)}"


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando contratos de obra…")
def datos() -> pd.DataFrame:
    """Tabla de modelado (data/processed/obra_modelo.csv) con columnas de apoyo."""
    t = cargar()
    t["mes_num"] = pd.to_numeric(t["mes"], errors="coerce").astype("Int64")
    t["decil_valor"] = pd.qcut(t["valor_inicial"].rank(method="first"), 10,
                               labels=range(1, 11)).astype("Int64")
    t["rango_plazo"] = pd.cut(t["plazo_inicial"], BINS_PLAZO,
                              labels=ETIQ_PLAZO)
    t["extension_plazo"] = (t["dias_adic"] / t["plazo_inicial"]).where(
        (t["y_tiempo"] == 1) & (t["plazo_inicial"] > 0))
    return t


def tabla_disponible() -> bool:
    try:
        datos()
        return True
    except FileNotFoundError:
        st.error(
            "No se encontró `data/processed/obra_modelo.csv`. Descargue los "
            "datos con `dvc pull` y genere la tabla con "
            "`python src/features.py`.")
        return False


def filtros_globales(t: pd.DataFrame):
    """Filtros de la barra lateral del mockup v2; se comparten entre vistas."""
    sb = st.sidebar
    sb.markdown("#### Filtros globales")
    a_min, a_max = int(t["anio"].min()), int(t["anio"].max())
    sb.slider("Año de firma", a_min, a_max, (a_min, a_max), key="f_anios")
    sb.multiselect("Departamento", sorted(t["departamento"].dropna().unique()),
                   key="f_deps", placeholder="Todos")
    sb.multiselect("Modalidad", sorted(t["modalidad"].dropna().unique()),
                   key="f_mods", placeholder="Todas")
    entidades = t["nombre_entidad"].value_counts().index.tolist()
    sb.multiselect("Entidad", entidades, key="f_ents", placeholder="Todas")
    sb.radio("Tipo de adición", list(TIPOS), key="f_tipo")


def filtrar(t: pd.DataFrame) -> pd.DataFrame:
    s = st.session_state
    a0, a1 = s.get("f_anios", (t["anio"].min(), t["anio"].max()))
    m = t["anio"].between(a0, a1)
    if s.get("f_deps"):
        m &= t["departamento"].isin(s["f_deps"])
    if s.get("f_mods"):
        m &= t["modalidad"].isin(s["f_mods"])
    if s.get("f_ents"):
        m &= t["nombre_entidad"].isin(s["f_ents"])
    return t[m]


def objetivo_actual():
    return TIPOS[st.session_state.get("f_tipo", "Cualquiera")]


def resumen_filtros() -> str:
    s = st.session_state
    partes = [f"{s['f_anios'][0]}–{s['f_anios'][1]}"] if "f_anios" in s else []
    for clave, nombre in [("f_deps", "departamentos"), ("f_mods", "modalidades"),
                          ("f_ents", "entidades")]:
        if s.get(clave):
            v = s[clave]
            partes.append(v[0] if len(v) == 1 else f"{len(v)} {nombre}")
    return ", ".join(partes)


def tasa_por(t: pd.DataFrame, col, objetivo, n_min=0) -> pd.DataFrame:
    g = (t.groupby(col, observed=True)[objetivo]
         .agg(tasa="mean", n="size").reset_index())
    return g[g["n"] >= n_min]


# --------------------------------------------------------------------------
# Predicciones: modelos locales o API
# --------------------------------------------------------------------------
# Sin API_URL, el tablero carga los modelos de models/ (app/prediccion.py).
# Con API_URL (Entrega 3), pide las mismas predicciones a la API.
class ErrorPrediccion(Exception):
    pass


def usa_api() -> bool:
    return API_URL is not None


def _post(ruta, cuerpo, **params):
    import requests
    try:
        r = requests.post(f"{API_URL}{ruta}", json=cuerpo, params=params,
                          timeout=120)
    except requests.ConnectionError:
        raise ErrorPrediccion(f"No hay conexión con la API en {API_URL}.")
    if r.status_code != 200:
        raise ErrorPrediccion(f"La API respondió {r.status_code}: {r.text}")
    return r.json()


@st.cache_data(ttl=30, show_spinner=False)
def estado_modelos():
    """Estado de la fuente de predicciones para la barra lateral."""
    if usa_api():
        import requests
        try:
            return requests.get(f"{API_URL}/health", timeout=5).json()
        except Exception:
            return None
    return prediccion.estado()


def predecir_contrato(contrato: dict) -> dict:
    contrato = _sin_nan(contrato)
    if usa_api():
        return _post("/predict", contrato, factores="true", n=6)
    try:
        return prediccion.predecir_contrato(contrato)
    except prediccion.ErrorModelo as e:
        raise ErrorPrediccion(str(e))


MANTENER_NULO = {"tasa_entidad"}  # vacía a propósito: entidad sin historia previa


def _sin_nan(d: dict) -> dict:
    """Quita los campos vacíos salvo los que deben conservarse vacíos."""
    limpio = {k: (None if isinstance(v, float) and math.isnan(v) else v)
              for k, v in d.items()}
    return {k: v for k, v in limpio.items()
            if v is not None or k in MANTENER_NULO}


CAMPOS_LOTE = ["id_contrato", "valor_inicial", "plazo_inicial", "respuestas",
               "inicial_sobre_base", "dias_publicacion_adjudicacion",
               "nombre_entidad", "tasa_entidad", "previos_entidad",
               "antiguedad_prov", "modalidad", "departamento",
               "segmento_unspsc", "destino_gasto", "condiciones_de_entrega",
               "es_pyme", "mes"]


@st.cache_data(show_spinner="Calculando el riesgo de los contratos…",
               ttl=3600)
def predecir_lote(registros: pd.DataFrame, tam=5000) -> pd.DataFrame:
    """Riesgo de varios contratos. Usa la tasa de la entidad de la tabla,
    calculada solo con años anteriores a la firma."""
    if not usa_api():
        try:
            return prediccion.predecir_lote(registros[CAMPOS_LOTE])
        except prediccion.ErrorModelo as e:
            raise ErrorPrediccion(str(e))
    cuerpo = registros[CAMPOS_LOTE].astype(object).where(
        registros[CAMPOS_LOTE].notna(), None)
    salidas = []
    for i in range(0, len(cuerpo), tam):
        parte = cuerpo.iloc[i:i + tam].to_dict(orient="records")
        salidas += _post("/predict/lote", {"contratos": parte})["resultados"]
    return pd.DataFrame(salidas)


# --------------------------------------------------------------------------
# Estilo
# --------------------------------------------------------------------------
CSS = f"""
<style>
[data-testid="stSidebar"] {{ background: {AZUL}; }}
[data-testid="stSidebar"] * {{ color: #F3F6FB; }}
[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] input {{ color: #1F2937; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background: {AZUL_MEDIO}; border-radius: 6px; }}
/* El pulgar del slider usa el color primario, igual al fondo de la barra */
[data-testid="stSidebar"] [data-testid="stSlider"] [role="group"] > div > div:first-child {{
  background: {AZUL_CLARO} !important; }}
[data-testid="stSidebar"] [data-testid="stSlider"] div[style*="translate(-50%, -50%)"] {{
  background: white !important; }}
.block-container {{ padding-top: 1.6rem; max-width: 1400px; }}
h1 {{ font-size: 1.55rem !important; color: {AZUL}; margin-bottom: .1rem; }}
h3 {{ font-size: 1.02rem !important; color: {AZUL}; }}
.letra {{ display: inline-flex; align-items: center; justify-content: center;
  width: 1.35rem; height: 1.35rem; border-radius: 50%; background: {ROJO};
  color: white; font-size: .75rem; font-weight: 700; margin-right: .45rem;
  vertical-align: 2px; }}
.kpi {{ border: 1px solid #E3E8F0; border-radius: 8px; padding: .7rem .9rem;
  background: white; min-height: 7.4rem; box-sizing: border-box; }}
.kpi .v {{ font-size: 1.65rem; font-weight: 700; color: {AZUL};
  line-height: 1.15; }}
.kpi .l {{ font-size: .82rem; color: {GRIS}; }}
.nota {{ background: #FFF6DB; border-left: 3px solid {AMBAR};
  padding: .45rem .7rem; font-size: .84rem; border-radius: 4px;
  margin: .3rem 0 .4rem; }}
.badge {{ display: inline-block; padding: .2rem .65rem; border-radius: 999px;
  color: white; font-weight: 700; font-size: .85rem;
  white-space: nowrap; }}
.prob {{ font-size: 2.6rem; font-weight: 800; line-height: 1; }}
.sub {{ color: {GRIS}; font-size: .84rem; }}
</style>
"""


def estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def titulo_panel(letra: str, texto: str):
    st.markdown(f"### <span class='letra'>{letra}</span>{texto}",
                unsafe_allow_html=True)


def nota(texto: str):
    st.markdown(f"<div class='nota'>{texto}</div>", unsafe_allow_html=True)


def kpi(valor: str, etiqueta: str):
    st.markdown(f"<div class='kpi'><div class='v'>{valor}</div>"
                f"<div class='l'>{etiqueta}</div></div>",
                unsafe_allow_html=True)


def badge(nivel: str, texto: str):
    return (f"<span class='badge' style='background:{NIVELES[nivel]}'>"
            f"{texto}</span>")
