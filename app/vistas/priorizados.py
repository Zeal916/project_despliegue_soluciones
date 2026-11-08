import plotly.graph_objects as go
import streamlit as st

import comun as c
from vistas import evaluar

COLUMNAS = ["id_contrato", "firma", "nombre_entidad", "departamento",
            "modalidad", "valor_inicial", "plazo_inicial"]
VISIBLES = ["id_contrato", "firma", "nombre_entidad", "departamento",
            "modalidad", "valor_mm", "plazo_inicial"]
ORDEN = {"Cualquiera": "riesgo_total", "En tiempo": "p_tiempo",
         "En valor": "p_valor"}


def vista():
    t = c.filtrar(c.datos())
    tipo = st.session_state.get("f_tipo", "Cualquiera")
    obj, nombre_obj = c.objetivo_actual()

    st.title("Contratos priorizados por riesgo de adición")
    st.caption(f"Contratos de obra firmados en {c.resumen_filtros()}, "
               f"ordenados por la probabilidad de {nombre_obj} que estima "
               "el modelo. Use los filtros de la barra lateral para acotar el "
               "conjunto.")
    if t.empty:
        st.info("Ningún contrato cumple los filtros. Amplíe el rango de años "
                "o quite algún filtro de la barra lateral.")
        return
    try:
        pred = c.predecir_lote(t)
    except c.ErrorPrediccion as e:
        st.error(str(e))
        return

    lista = (t[COLUMNAS + ["y", "y_tiempo", "y_valor"]].reset_index(drop=True)
             .join(pred.drop(columns="id_contrato"))
             .sort_values(ORDEN[tipo], ascending=False, ignore_index=True))
    lista.insert(0, "puesto", lista.index + 1)
    lista["valor_mm"] = lista["valor_inicial"] / 1e6

    a, b, d = st.columns([1, 1, 2])
    k = a.number_input("Capacidad de revisión (k contratos)", 10,
                       max(10, len(lista)), min(100, len(lista)), step=10,
                       help="Número de contratos que el equipo puede revisar.")
    solo_alerta = b.toggle("Solo alerta alta", value=False,
                           help="Percentil 90 o más frente a 2025.")
    mostrar_real = d.toggle(
        "Mostrar desenlace registrado (validación histórica)", value=False,
        help="Estos contratos ya terminaron: comparar con su desenlace "
             "muestra cuánto ayuda priorizar. El modelo no lo usa.")

    top = lista.head(int(k))
    if mostrar_real and lista["firma"].dt.year.min() < 2025:
        c.nota("Los contratos de 2019 a 2024 se usaron para entrenar el "
               "modelo, así que su precisión es optimista. Para una "
               "validación honesta, deje solo 2025 en «Año de firma».")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        c.kpi(c.entero(len(lista)), "contratos en el filtro")
    with m2:
        c.kpi(c.entero((lista["nivel_alerta"] == "alta").sum()),
              "con alerta alta (percentil ≥ 90)")
    with m3:
        c.kpi(c.pct(top[obj].mean()) if mostrar_real else "—",
              f"con {nombre_obj} entre los {k} primeros (registrado)")
    with m4:
        base = lista[obj].mean()
        c.kpi(f"{top[obj].mean() / base:.2f}".replace(".", ",") + "×"
              if base and mostrar_real else "—",
              f"lift frente a la tasa del filtro ({c.pct(base)})")

    # Curva de precisión en k: cuánto se gana al priorizar con el modelo.
    if mostrar_real:
        with st.expander("Precisión según la capacidad de revisión"):
            ks = sorted({x for x in [25, 50, 100, 200, 300, 500, 750, 1000,
                                     2000, 5000] if x <= len(lista)}
                        | {len(lista)})
            fig = go.Figure(go.Scatter(
                x=ks, y=[lista[obj].head(x).mean() for x in ks],
                mode="lines+markers", line_color=c.ROJO,
                hovertemplate="k=%{x}: %{y:.1%}<extra></extra>"))
            fig.add_hline(y=base, line_dash="dot", line_color=c.GRIS,
                          annotation_text=f"Al azar ({c.pct(base)})")
            fig.update_layout(height=280, xaxis=dict(type="log", title="k"),
                              yaxis=dict(tickformat=".0%",
                                         title="Precisión"))
            st.plotly_chart(fig, width="stretch")

    vista_lista = lista[lista["nivel_alerta"] == "alta"] if solo_alerta \
        else lista
    columnas = ["puesto"] + VISIBLES + ["riesgo_total", "p_tiempo", "p_valor",
                                        "percentil", "nivel_alerta"]
    if mostrar_real:
        columnas += ["y_tiempo", "y_valor"]
    sel = st.dataframe(
        vista_lista[columnas], hide_index=True, width="stretch",
        height=460, on_select="rerun", selection_mode="single-row",
        column_config={
            "puesto": st.column_config.NumberColumn("#", width="small"),
            "id_contrato": "ID del contrato",
            "firma": st.column_config.DateColumn("Firma", format="DD/MM/YYYY"),
            "nombre_entidad": st.column_config.TextColumn("Entidad",
                                                          width="medium"),
            "departamento": "Departamento", "modalidad": "Modalidad",
            "valor_mm": st.column_config.NumberColumn(
                "Valor inicial (millones)", format="%.0f"),
            "plazo_inicial": st.column_config.NumberColumn("Plazo (días)",
                                                           format="%d"),
            "riesgo_total": st.column_config.ProgressColumn(
                "Riesgo total", format="percent", min_value=0, max_value=1),
            "p_tiempo": st.column_config.NumberColumn("P(tiempo)",
                                                      format="percent"),
            "p_valor": st.column_config.NumberColumn("P(valor)",
                                                     format="percent"),
            "percentil": st.column_config.NumberColumn("Percentil",
                                                       format="percent"),
            "nivel_alerta": "Alerta",
            "y_tiempo": st.column_config.CheckboxColumn("Prórroga real"),
            "y_valor": st.column_config.CheckboxColumn("Adición valor real"),
        })

    filas = sel.selection.rows if sel and sel.selection else []
    a, b = st.columns([1, 1])
    if filas:
        elegido = vista_lista.iloc[filas[0]]["id_contrato"]
        if a.button(f"Evaluar {elegido} en detalle", type="primary"):
            evaluar.precargar(elegido)
            st.switch_page(st.session_state["pagina_evaluar"])
    else:
        a.caption("Seleccione una fila para abrir su evaluación detallada "
                  "con factores SHAP.")
    descarga = vista_lista[columnas].copy()
    b.download_button(
        "Descargar lista (CSV)", descarga.to_csv(index=False).encode("utf-8"),
        file_name="contratos_priorizados.csv", mime="text/csv",
        width="stretch")
