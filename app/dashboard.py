import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comun as c  # noqa: E402
from vistas import evaluar, panorama, priorizados  # noqa: E402

st.set_page_config(page_title="Alerta de adiciones en obra pública",
                   page_icon="🏗️", layout="wide")
c.estilo()

st.sidebar.markdown("## Alerta de adiciones")
st.sidebar.caption("Contratos de obra pública en SECOP II")

if not c.tabla_disponible():
    st.stop()

paginas = {
    "panorama": st.Page(panorama.vista, title="Panorama de obras",
                        icon=":material/map:", default=True),
    "evaluar": st.Page(evaluar.vista, title="Evaluar un contrato",
                       icon=":material/fact_check:", url_path="evaluar"),
    "priorizados": st.Page(priorizados.vista, title="Contratos priorizados",
                           icon=":material/format_list_numbered:",
                           url_path="priorizados"),
}
st.session_state["pagina_evaluar"] = paginas["evaluar"]
navegacion = st.navigation(list(paginas.values()), position="hidden")
for pagina in paginas.values():
    st.sidebar.page_link(pagina)
st.sidebar.divider()

c.filtros_globales(c.datos())

estado = c.estado_modelos()
fuente = f"API en {c.API_URL}" if c.usa_api() else "modelos locales (models/)"
if estado and estado.get("estado") == "ok":
    st.sidebar.caption(f"Predicciones con {fuente}. Percentiles frente a "
                       f"{c.entero(estado['contratos_referencia'])} contratos "
                       f"de {estado['anio_referencia']}.")
else:
    detalle = estado.get("detalle") if estado else "sin conexión"
    st.sidebar.warning(f"Predicciones no disponibles ({fuente}): {detalle}. "
                       "El panorama funciona; las vistas 2 y 3 las necesitan.")

navegacion.run()
