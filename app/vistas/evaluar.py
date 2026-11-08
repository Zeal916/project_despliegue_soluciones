import datetime as dt
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun as c

SIN_DATO = "(Sin dato)"
ENTIDAD_NUEVA = "(Entidad sin historia en SECOP II)"
OBJ_TIPO = {"Cualquiera": "y", "En tiempo": "y_tiempo", "En valor": "y_valor"}


# --------------------------------------------------------------------------
# Precarga por ID (elemento G)
# --------------------------------------------------------------------------
def _opcion(valor, opciones):
    return valor if isinstance(valor, str) and valor in opciones else SIN_DATO


def _num(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) \
        else float(v)


def precargar(id_contrato: str) -> bool:
    """Llena el formulario con un contrato de la tabla de modelado.

    Solo se precargan variables conocidas al firmar. La tasa y la
    experiencia de la entidad son las de la tabla, calculadas con años
    anteriores a la firma, para no usar el desenlace del propio contrato.
    """
    t = c.datos()
    fila = t[t["id_contrato"] == id_contrato.strip()]
    if fila.empty:
        st.session_state["g_aviso"] = (
            f"No se encontró el contrato {id_contrato} en la tabla de "
            "modelado (contratos de obra 2019 a 2025).")
        return False
    f = fila.iloc[0]
    s = st.session_state
    ents = set(t["nombre_entidad"].dropna())
    s["g_entidad"] = f["nombre_entidad"] if f["nombre_entidad"] in ents \
        else ENTIDAD_NUEVA
    s["g_modalidad"] = f["modalidad"]
    s["g_departamento"] = _opcion(f["departamento"],
                                  set(t["departamento"].dropna()))
    s["g_valor"] = _num(f["valor_inicial"])
    s["g_plazo"] = _num(f["plazo_inicial"])
    s["g_fecha"] = f["firma"].date()
    s["g_respuestas"] = _num(f["respuestas"])
    s["g_isb"] = _num(f["inicial_sobre_base"])
    s["g_dpa"] = _num(f["dias_publicacion_adjudicacion"])
    s["g_antig"] = _num(f["antiguedad_prov"])
    s["g_unspsc"] = _opcion(f["segmento_unspsc"],
                            set(t["segmento_unspsc"].dropna()))
    s["g_destino"] = _opcion(f["destino_gasto"],
                             set(t["destino_gasto"].dropna()))
    s["g_condiciones"] = _opcion(f["condiciones_de_entrega"],
                                 set(t["condiciones_de_entrega"].dropna()))
    s["g_pyme"] = _opcion(f["es_pyme"], set(t["es_pyme"].dropna()))
    s["g_precarga"] = {
        "id_contrato": f["id_contrato"], "entidad": f["nombre_entidad"],
        "tasa_entidad": _num(f["tasa_entidad"]),
        "previos_entidad": _num(f["previos_entidad"]),
        "y": int(f["y"]), "y_tiempo": int(f["y_tiempo"]),
        "y_valor": int(f["y_valor"]), "dias_adic": _num(f["dias_adic"]),
    }
    s["g_id"] = f["id_contrato"]
    s.pop("g_resultado", None)
    s.pop("g_aviso", None)
    return True


def _al_precargar():
    precargar(st.session_state.get("g_id", ""))


def _limpiar():
    for k in list(st.session_state):
        if k.startswith("g_") and k != "g_id":
            del st.session_state[k]
    st.session_state["g_id"] = ""


# --------------------------------------------------------------------------
# Formulario (elemento G)
# --------------------------------------------------------------------------
def _opciones(t, col):
    return [SIN_DATO] + t[col].dropna().value_counts().index.tolist()


def formulario(t: pd.DataFrame):
    c.titulo_panel("G", "Datos conocidos al firmar")
    col1, col2 = st.columns([3, 1.2], vertical_alignment="bottom")
    col1.text_input("Precargar por ID del contrato",
                    placeholder="CO1.PCCNTR.8645608", key="g_id")
    col2.button("Precargar", on_click=_al_precargar,
                width="stretch")
    if st.session_state.get("g_aviso"):
        st.warning(st.session_state["g_aviso"])

    entidades = [ENTIDAD_NUEVA] + t["nombre_entidad"].value_counts() \
        .index.tolist()
    modalidades = t["modalidad"].dropna().value_counts().index.tolist()
    s = st.session_state
    s.setdefault("g_modalidad", modalidades[0])
    s.setdefault("g_fecha", dt.date.today())
    for clave in ["g_valor", "g_plazo", "g_respuestas", "g_isb", "g_dpa",
                  "g_antig"]:
        s.setdefault(clave, None)

    with st.form("formulario_g", border=False):
        st.selectbox("Entidad contratante", entidades, key="g_entidad",
                     help="Escrita como en SECOP II. Con ella se calcula la "
                          "tasa histórica de adición de la entidad.")
        st.selectbox("Modalidad de selección", modalidades, key="g_modalidad")
        st.selectbox("Departamento", _opciones(t, "departamento"),
                     key="g_departamento")
        a, b = st.columns(2)
        a.number_input("Valor inicial (COP)", min_value=0.0, step=1e7,
                       format="%.0f", key="g_valor", placeholder="500000000")
        b.number_input("Plazo inicial (días), opcional", min_value=1.0,
                       max_value=3650.0, step=15.0, format="%.0f",
                       key="g_plazo")
        a, b = st.columns(2)
        a.date_input("Fecha de firma", key="g_fecha", format="DD/MM/YYYY")
        b.number_input("Respuestas al proceso", min_value=0.0, step=1.0,
                       format="%.0f", key="g_respuestas")
        with st.expander("Proceso y proveedor (opcionales)"):
            a, b = st.columns(2)
            a.number_input("Valor adjudicado / precio base", min_value=0.0,
                           max_value=10.0, step=0.01, format="%.3f",
                           key="g_isb",
                           help="Por ejemplo 0,95 si se adjudicó 5 % por "
                                "debajo del precio base.")
            b.number_input("Días de publicación a adjudicación",
                           min_value=0.0, step=1.0, format="%.0f",
                           key="g_dpa")
            a.number_input("Antigüedad del proveedor (años)", min_value=0.0,
                           step=0.5, format="%.1f", key="g_antig")
            b.selectbox("Proveedor pyme", _opciones(t, "es_pyme"),
                        key="g_pyme")
            st.selectbox("Segmento UNSPSC (2 dígitos)",
                         _opciones(t, "segmento_unspsc"), key="g_unspsc")
            a, b = st.columns(2)
            a.selectbox("Destino del gasto", _opciones(t, "destino_gasto"),
                        key="g_destino")
            b.selectbox("Condiciones de entrega",
                        _opciones(t, "condiciones_de_entrega"),
                        key="g_condiciones")
        enviado = st.form_submit_button("Calcular riesgo de adición",
                                        type="primary",
                                        width="stretch")
    st.button("Limpiar formulario", on_click=_limpiar, type="tertiary")
    c.nota("Sin estado del contrato, días adicionados ni fecha de inicio: "
           "no se conocen al firmar y delatan el desenlace.")
    return enviado


def contrato_desde_formulario() -> dict:
    s = st.session_state

    def cat(clave):
        v = s.get(clave)
        return None if v in (None, SIN_DATO) else v

    entidad = s.get("g_entidad")
    contrato = {
        "nombre_entidad": None if entidad == ENTIDAD_NUEVA else entidad,
        "modalidad": cat("g_modalidad"),
        "departamento": cat("g_departamento"),
        "valor_inicial": s.get("g_valor"),
        "plazo_inicial": s.get("g_plazo"),
        "mes": s["g_fecha"].month if s.get("g_fecha") else None,
        "respuestas": s.get("g_respuestas"),
        "inicial_sobre_base": s.get("g_isb"),
        "dias_publicacion_adjudicacion": s.get("g_dpa"),
        "antiguedad_prov": s.get("g_antig"),
        "segmento_unspsc": cat("g_unspsc"),
        "destino_gasto": cat("g_destino"),
        "condiciones_de_entrega": cat("g_condiciones"),
        "es_pyme": cat("g_pyme"),
    }
    pre = s.get("g_precarga")
    if pre and pre["entidad"] == entidad:
        contrato["id_contrato"] = pre["id_contrato"]
        contrato["tasa_entidad"] = pre["tasa_entidad"]
        contrato["previos_entidad"] = pre["previos_entidad"]
    if entidad == ENTIDAD_NUEVA:
        contrato["previos_entidad"] = 0
    return contrato


# --------------------------------------------------------------------------
# Resultado (elementos H a K)
# --------------------------------------------------------------------------
def _valor_legible(variable, valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "sin dato"
    if variable == "log_valor_inicial":
        return c.pesos(10 ** valor)
    if variable in ("tasa_entidad",):
        return c.pct(valor)
    if variable == "inicial_sobre_base":
        return f"{valor:.2f}".replace(".", ",")
    if variable == "mes":
        try:
            return c.MESES[int(valor) - 1]
        except (ValueError, IndexError):
            return str(valor)
    if isinstance(valor, float):
        return c.entero(valor)
    return str(valor)


def panel_h(r):
    c.titulo_panel("H", "Probabilidad estimada de adición")
    nivel = r["nivel_alerta"]
    color = c.NIVELES[nivel]
    percentil = round(100 * r["percentil"])
    a, b = st.columns([1.3, 1])
    with a:
        st.markdown(
            f"<div class='prob' style='color:{color}'>"
            f"{c.pct(r['riesgo_total'], 0)}</div>"
            f"<div class='sub'>riesgo total, máximo de los tres modelos</div>"
            f"<div style='margin-top:.5rem'>"
            f"{c.badge(nivel, f'Alerta {nivel}, p{min(percentil, 99)}')}"
            f"</div>", unsafe_allow_html=True)
    with b:
        p, q = r["probabilidades"], r["percentiles"]
        st.markdown(
            f"<div class='sub'>En tiempo</div><b style='font-size:1.3rem'>"
            f"{c.pct(p['y_tiempo'], 0)}</b> <span class='sub'>p"
            f"{min(round(100 * q['y_tiempo']), 99)}</span><br>"
            f"<div class='sub' style='margin-top:.35rem'>En valor</div>"
            f"<b style='font-size:1.3rem'>{c.pct(p['y_valor'], 0)}</b> "
            f"<span class='sub'>p{min(round(100 * q['y_valor']), 99)}</span>",
            unsafe_allow_html=True)
    st.caption("Semáforo por percentil frente a los contratos de 2025: alta "
               "en el 10 % de mayor riesgo (precisión de 0,725 en la prueba), "
               "media entre el 70 % y el 90 %. La lectura principal es el "
               "percentil: la probabilidad subestima la tasa de 2025 aun "
               "recalibrada.")


def panel_i(r, objetivo):
    c.titulo_panel("I", "¿Por qué? Factores que más aportan (SHAP local)")
    f = pd.DataFrame(r["factores"][objetivo])
    f["texto"] = [f"{e} = {_valor_legible(v, x)}" for e, v, x in
                  zip(f["etiqueta"], f["variable"], f["valor"])]
    f = f.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=f["aporte"], y=f["texto"], orientation="h",
        marker_color=[c.ROJO if a > 0 else c.AZUL_MEDIO for a in f["aporte"]],
        hovertemplate="%{y}<br>Aporte %{x:+.3f} log-odds<extra></extra>"))
    fig.add_vline(x=0, line_color=c.GRIS, line_width=1)
    fig.update_layout(height=70 + 38 * len(f), yaxis_title=None,
                      xaxis_title="Aporte al riesgo (log-odds)",
                      margin=dict(l=0, r=10, t=10, b=40))
    st.plotly_chart(fig, width="stretch",
                    config={"displayModeBar": False})
    nombre = {"y": "total", "y_tiempo": "en tiempo", "y_valor": "en valor"}
    st.caption(f"Modelo {nombre[objetivo]}. Rojo sube el riesgo y azul lo "
               "baja frente a una muestra de 300 contratos de 2019 a 2024. "
               "Cambie el tipo de adición en la barra lateral para ver los "
               "factores de cada modelo.")


def _similares(t, contrato):
    """Contratos con la misma modalidad, decil de valor y departamento.

    Si quedan menos de 30, se relaja primero el departamento y luego el decil.
    """
    criterios = []
    m = pd.Series(True, index=t.index)
    if contrato.get("modalidad"):
        m &= t["modalidad"] == contrato["modalidad"]
        criterios.append("misma modalidad")
    m_dec = pd.Series(True, index=t.index)
    if contrato.get("valor_inicial"):
        bordes = np.quantile(t["valor_inicial"].dropna(),
                             np.linspace(0, 1, 11))
        dec = int(np.clip(np.searchsorted(bordes, contrato["valor_inicial"],
                                          side="right"), 1, 10))
        m_dec = t["decil_valor"] == dec
    m_dep = (t["departamento"] == contrato["departamento"]) \
        if contrato.get("departamento") else pd.Series(True, index=t.index)
    for usa_dec, usa_dep in [(True, True), (True, False), (False, False)]:
        mm = m & (m_dec if usa_dec else True) & (m_dep if usa_dep else True)
        if mm.sum() >= 30 or not (usa_dec or usa_dep):
            extra = (["rango de valor"] if usa_dec and
                     contrato.get("valor_inicial") else []) + \
                (["departamento"] if usa_dep and contrato.get("departamento")
                 else [])
            return t[mm], criterios + extra
    return t[m], criterios


def panel_j(t, contrato):
    c.titulo_panel("J", "Comparación con contratos similares y con la entidad")
    sim, criterios = _similares(t, contrato)
    grupos = [("Contratos similares", sim)]
    if contrato.get("nombre_entidad"):
        grupos.append(("La entidad",
                       t[t["nombre_entidad"] == contrato["nombre_entidad"]]))
    grupos.append(("Todas las obras", t))
    fig = go.Figure()
    for col, nombre, color in [("y", "Total", c.AZUL), ("y_tiempo", "Tiempo",
                               c.AZUL_MEDIO), ("y_valor", "Valor", c.AMBAR)]:
        fig.add_bar(name=nombre, x=[f"{g} (n={c.entero(len(d))})"
                                    for g, d in grupos],
                    y=[d[col].mean() if len(d) else None for _, d in grupos],
                    marker_color=color,
                    text=[c.pct(d[col].mean(), 0) if len(d) else ""
                          for _, d in grupos], textposition="outside",
                    hovertemplate="%{x}<br>" + nombre +
                                  ": %{y:.1%}<extra></extra>")
    fig.update_layout(barmode="group", height=300, yaxis_tickformat=".0%",
                      legend=dict(orientation="h", y=1.15),
                      yaxis_range=[0, 1.05])
    st.plotly_chart(fig, width="stretch",
                    config={"displayModeBar": False})
    n_ent = len(grupos[1][1]) if len(grupos) == 3 else 0
    texto = (f"Similares: {', '.join(criterios) or 'todos los contratos'}. ")
    if contrato.get("nombre_entidad") and n_ent < 30:
        texto += (f"La entidad tiene solo {n_ent} contratos de obra: su tasa "
                  "se suaviza hacia la tasa global para que la alerta no se "
                  "lea como «qué entidad firma».")
    else:
        texto += ("Se muestra el n de cada grupo para que la alerta no se lea "
                  "solo como «qué entidad firma».")
    c.nota(texto)
    return sim


def panel_k(t, contrato, r, objetivo):
    c.titulo_panel("K", "Lectura sugerida para el veedor")
    nivel = r["nivel_alerta"]
    top = 100 - round(100 * r["percentil"])
    lineas = []
    if nivel == "alta":
        lineas.append(
            f"**Priorizar.** El contrato queda en el {max(top, 1)} % de mayor "
            "riesgo frente a los contratos de 2025. Conviene revisar estudios "
            "previos, cronograma y disponibilidad presupuestal antes del "
            "inicio de la ejecución.")
    elif nivel == "media":
        lineas.append(
            f"**Seguimiento cercano.** Está en el {top} % de mayor riesgo, "
            "fuera del umbral de alerta. Programe una revisión del "
            "cronograma en el primer tercio del plazo.")
    else:
        lineas.append("**Seguimiento ordinario.** Su riesgo relativo es bajo "
                      "frente a los contratos de 2025.")
    p = r["probabilidades"]
    base_t, base_v = t["y_tiempo"].mean(), t["y_valor"].mean()
    if p["y_tiempo"] / base_t >= p["y_valor"] / base_v:
        lineas.append(f"El riesgo dominante es una **prórroga** "
                      f"({c.pct(p['y_tiempo'], 0)} frente a una tasa de "
                      f"{c.pct(base_t, 0)}).")
    else:
        lineas.append(f"El riesgo dominante es una **adición en valor** "
                      f"({c.pct(p['y_valor'], 0)} frente a una tasa de "
                      f"{c.pct(base_v, 0)}); el tope legal es el 50 % del "
                      "valor inicial.")
    sube = [f for f in r["factores"][objetivo] if f["aporte"] > 0][:2]
    if sube:
        lineas.append("Lo que más sube el riesgo: " + "; ".join(
            f"{f['etiqueta'].lower()} ({_valor_legible(f['variable'], f['valor'])})"
            for f in sube) + ".")
    mes = contrato.get("mes")
    if mes in (11, 12):
        tasa_mes = t.loc[t["mes_num"] == mes, "y_tiempo"].mean()
        lineas.append(
            f"Firmado en {c.MESES[mes - 1].lower()}, al cierre de la vigencia "
            f"fiscal: la tasa histórica de prórroga ese mes es "
            f"{c.pct(tasa_mes)} frente a {c.pct(base_t)} en todo el año.")
    if not r.get("entidad_con_historia"):
        lineas.append("La entidad no tiene contratos de obra en la historia: "
                      "el modelo usa la tasa global de adición.")
    lineas.append("La alerta indica dónde mirar primero; el criterio final es "
                  "del equipo de control.")
    st.markdown("\n\n".join(lineas))


def desenlace_registrado():
    pre = st.session_state.get("g_precarga")
    if not pre:
        return
    partes = []
    if pre["y_tiempo"]:
        partes.append(f"prórroga de {c.entero(pre['dias_adic'] or 0)} días")
    if pre["y_valor"]:
        partes.append("adición en valor")
    texto = ", ".join(partes) if partes else "sin adiciones"
    st.caption(f"Desenlace registrado de {pre['id_contrato']} (el modelo no "
               f"lo usa): {texto}.")


# --------------------------------------------------------------------------
def vista():
    t = c.datos()
    st.title("Evaluar un contrato al momento de la firma")
    izq, der = st.columns([1, 1.9], gap="large")
    with izq:
        enviado = formulario(t)
    if enviado:
        contrato = contrato_desde_formulario()
        if not contrato.get("valor_inicial"):
            der.warning("Ingrese al menos el valor inicial del contrato: es "
                        "la variable que más pesa en el modelo.")
        else:
            try:
                with der, st.spinner("Calculando el riesgo…"):
                    st.session_state["g_resultado"] = (
                        contrato, c.predecir_contrato(contrato))
            except c.ErrorPrediccion as e:
                der.error(str(e))
    with der:
        if "g_resultado" not in st.session_state:
            st.info("Diligencie el formulario o precargue un contrato por su "
                    "ID y pulse «Calcular riesgo de adición». El tablero "
                    "muestra la probabilidad, el percentil, los factores y "
                    "la comparación histórica.")
            return
        contrato, r = st.session_state["g_resultado"]
        objetivo = OBJ_TIPO[st.session_state.get("f_tipo", "Cualquiera")]
        a, b = st.columns([1, 1.45], gap="medium")
        with a:
            panel_h(r)
            desenlace_registrado()
        with b:
            panel_i(r, objetivo)
        panel_j(t, contrato)
        panel_k(t, contrato, r, objetivo)
