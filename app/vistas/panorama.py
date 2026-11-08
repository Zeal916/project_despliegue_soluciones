import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import comun as c


def _barras_h(df, etiqueta, tasa_base, alto):
    df = df.sort_values("tasa")
    fig = go.Figure(go.Bar(
        x=df["tasa"], y=df[etiqueta], orientation="h",
        marker_color=c.AZUL_MEDIO,
        text=[f"{c.pct(t, 0)}  (n={c.entero(n)})"
              for t, n in zip(df["tasa"], df["n"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Tasa %{x:.1%}<extra></extra>"))
    fig.add_vline(x=tasa_base, line_dash="dot", line_color=c.ROJO,
                  annotation_text=f"Tasa base {c.pct(tasa_base)}",
                  annotation_position="top", annotation_font_color=c.ROJO)
    fig.update_layout(height=alto, xaxis_tickformat=".0%",
                      xaxis_range=[0, min(1, df["tasa"].max() * 1.35)],
                      yaxis_title=None, xaxis_title=None)
    return fig


def vista():
    t_total = c.datos()
    t = c.filtrar(t_total)
    obj, nombre_obj = c.objetivo_actual()

    st.title("Panorama: ¿dónde se concentran las adiciones?")
    st.caption(f"Contratos de obra de SECOP II firmados en "
               f"{c.resumen_filtros()}. Tipo de adición: {nombre_obj}.")
    if t.empty:
        st.info("Ningún contrato cumple los filtros. Amplíe el rango de años "
                "o quite algún filtro de la barra lateral.")
        return
    base = t[obj].mean()

    # A. Indicadores ------------------------------------------------------
    c.titulo_panel("A", "Indicadores")
    k1, k2, k3, k4, k5 = st.columns([1, 1, 1, 1, 1.6])
    with k1:
        c.kpi(c.entero(len(t)), "contratos de obra analizados")
    with k2:
        c.kpi(c.pct(base), f"con {nombre_obj} (tasa base)")
    with k3:
        c.kpi(c.pct(t["y_tiempo"].mean()),
              f"en tiempo; {c.pct(t['y_valor'].mean())} en valor")
    with k4:
        ext = t["extension_plazo"].median()
        c.kpi(c.pct(ext, 0), "extensión mediana del plazo cuando hay prórroga")
    with k5:
        por_anio = c.tasa_por(t, "anio", obj)
        fig = go.Figure(go.Bar(
            x=por_anio["anio"], y=por_anio["tasa"], marker_color=c.AZUL_CLARO,
            text=[c.pct(v, 0) for v in por_anio["tasa"]],
            textposition="inside", insidetextanchor="end",
            hovertemplate="%{x}: %{y:.1%}<extra></extra>"))
        fig.update_layout(height=105, margin=dict(l=0, r=0, t=18, b=0),
                          yaxis_visible=False, xaxis_dtick=1,
                          title=dict(text="Tasa base por año de firma",
                                     font_size=12, x=0))
        st.plotly_chart(fig, width="stretch",
                        config={"displayModeBar": False})
    st.caption(f"Valor inicial contratado en el filtro: "
               f"{c.pesos(t['valor_inicial'].sum())}. La tasa de 2025 "
               "(prueba del modelo) es mayor por el cambio en la práctica de "
               "registro de prórrogas.")

    # B y C ---------------------------------------------------------------
    col_b, col_c = st.columns([1.25, 1])
    with col_b:
        c.titulo_panel("B", "Departamentos (barras por tasa, n mínimo)")
        n_min = st.slider("Contratos mínimos por departamento", 10, 500, 50,
                          step=10, key="n_min_dep")
        dep = c.tasa_por(t, "departamento", obj, n_min)
        if dep.empty:
            st.info(f"Ningún departamento tiene {n_min} contratos o más con "
                    "estos filtros. Baje el mínimo.")
        else:
            st.plotly_chart(_barras_h(dep, "departamento", base,
                                      max(260, 22 * len(dep))),
                            width="stretch")
            top = dep.sort_values("n", ascending=False).iloc[0]
            c.nota(f"{top['departamento']} concentra el "
                   f"{c.pct(top['n'] / len(t))} de los contratos, con "
                   f"{c.pct(top['tasa'])} de adición.")
    with col_c:
        c.titulo_panel("C", "Modalidad de selección")
        conteo = t["modalidad"].value_counts()
        grandes = conteo[conteo >= 100].index
        mod = c.tasa_por(t.assign(modalidad=t["modalidad"].where(
            t["modalidad"].isin(grandes), "Otras")), "modalidad", obj)
        st.plotly_chart(_barras_h(mod, "modalidad", base, 300),
                        width="stretch")
        c.nota("Modalidades con menos de 100 contratos se agrupan en "
               "«Otras». Cada barra muestra su n.")

    # D. Valor y plazo ----------------------------------------------------
    c.titulo_panel("D", "Tasa por decil de valor inicial y por valor × plazo")
    col_d1, col_d2 = st.columns([1, 1.3])
    with col_d1:
        dec = c.tasa_por(t, "decil_valor", obj)
        rangos = t.groupby("decil_valor", observed=True)["valor_inicial"] \
            .agg(["min", "max"])
        dec = dec.join(rangos, on="decil_valor")
        fig = go.Figure(go.Scatter(
            x=dec["decil_valor"], y=dec["tasa"], mode="lines+markers",
            line=dict(color=c.AZUL_MEDIO, width=3), marker_size=8,
            customdata=[[c.pesos(a), c.pesos(b), c.entero(n)] for a, b, n in
                        zip(dec["min"], dec["max"], dec["n"])],
            hovertemplate="Decil %{x}: %{y:.1%}<br>%{customdata[0]} a "
                          "%{customdata[1]}<br>n = %{customdata[2]}"
                          "<extra></extra>"))
        fig.update_layout(height=330, yaxis_tickformat=".0%",
                          xaxis=dict(dtick=1, title="Decil de valor inicial "
                                     "(1 = menor)"))
        st.plotly_chart(fig, width="stretch")
    with col_d2:
        cal = (t.groupby(["decil_valor", "rango_plazo"], observed=True)[obj]
               .agg(["mean", "size"]).reset_index())
        cal.loc[cal["size"] < 20, "mean"] = None
        z = cal.pivot(index="decil_valor", columns="rango_plazo",
                      values="mean").reindex(columns=c.ETIQ_PLAZO)
        nn = cal.pivot(index="decil_valor", columns="rango_plazo",
                       values="size").reindex(columns=c.ETIQ_PLAZO)
        fig = go.Figure(go.Heatmap(
            z=z.values, x=z.columns, y=[f"D{d}" for d in z.index],
            colorscale=[[0, "#FFF5E6"], [0.5, "#F39C4A"], [1, "#9B1C1C"]],
            zmin=0, zmax=max(0.5, float(z.max().max() or 0)),
            text=[[c.pct(v, 0) if v == v and v is not None else "" for v in fila]
                  for fila in z.values], texttemplate="%{text}",
            customdata=nn.values,
            hovertemplate="Decil %{y}, plazo %{x} días<br>Tasa %{z:.1%}"
                          "<br>n = %{customdata}<extra></extra>",
            colorbar=dict(tickformat=".0%", thickness=10)))
        fig.update_layout(height=330, xaxis_title="Plazo inicial (días)",
                          yaxis=dict(autorange="reversed",
                                     title="Decil de valor"))
        st.plotly_chart(fig, width="stretch")
    c.nota("Celdas con menos de 20 contratos quedan en blanco. El valor y el "
           "plazo son los pactados al firmar, no los actuales (que ya "
           "incluyen las adiciones).")

    # E y F ---------------------------------------------------------------
    col_e, col_f = st.columns([1.15, 1])
    with col_e:
        c.titulo_panel("E", "Estacionalidad por mes de firma")
        mes = (t.groupby("mes_num")
               .agg(n=("y", "size"), tiempo=("y_tiempo", "mean"),
                    valor=("y_valor", "mean")).reindex(range(1, 13))
               .reset_index())
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=c.MESES, y=mes["n"], name="Firmas",
                    marker_color=c.AZUL_CLARO,
                    hovertemplate="%{x}: %{y:,} firmas<extra></extra>")
        fig.add_scatter(x=c.MESES, y=mes["tiempo"], name="% en tiempo",
                        mode="lines+markers", line_color=c.ROJO,
                        secondary_y=True,
                        hovertemplate="%{x}: %{y:.1%}<extra>tiempo</extra>")
        fig.add_scatter(x=c.MESES, y=mes["valor"], name="% en valor",
                        mode="lines+markers", line_color=c.AMBAR,
                        secondary_y=True,
                        hovertemplate="%{x}: %{y:.1%}<extra>valor</extra>")
        fig.update_layout(height=320, legend=dict(orientation="h", y=1.12))
        fig.update_yaxes(title_text="Firmas", secondary_y=False)
        fig.update_yaxes(title_text="Tasa", tickformat=".0%",
                         secondary_y=True, showgrid=False)
        st.plotly_chart(fig, width="stretch")
        dic = mes.loc[11, "n"] / mes["n"].sum() if mes["n"].sum() else 0
        c.nota(f"Diciembre concentra el {c.pct(dic)} de las firmas, por el "
               "cierre de la vigencia fiscal.")
    with col_f:
        c.titulo_panel("F", "Entidades con mayor tasa de adición")
        n_ent = st.number_input("Contratos mínimos por entidad", 5, 1000, 30,
                                step=5, key="n_min_ent")
        ent = (t.groupby("nombre_entidad")
               .agg(contratos=("y", "size"), tasa=(obj, "mean"),
                    tiempo=("y_tiempo", "mean"), valor=("y_valor", "mean"))
               .query("contratos >= @n_ent")
               .sort_values(["tasa", "contratos"], ascending=False)
               .reset_index())
        st.dataframe(
            ent, hide_index=True, height=300, width="stretch",
            column_config={
                "nombre_entidad": st.column_config.TextColumn("Entidad",
                                                              width="medium"),
                "contratos": st.column_config.NumberColumn("Contratos"),
                "tasa": st.column_config.ProgressColumn(
                    "% adición", format="percent", min_value=0, max_value=1),
                "tiempo": st.column_config.NumberColumn("% tiempo",
                                                        format="percent"),
                "valor": st.column_config.NumberColumn("% valor",
                                                       format="percent"),
            })
        if len(ent):
            con_adic = t.groupby("nombre_entidad")[obj].sum() \
                .sort_values(ascending=False)
            c.nota(f"{c.entero(t['nombre_entidad'].nunique())} entidades; las "
                   f"10 con más adiciones aportan el "
                   f"{c.pct(con_adic.head(10).sum() / max(con_adic.sum(), 1))}"
                   " de los contratos con adición.")
