"""Tabla de modelado: un contrato de obra por fila con variables de firma.

Reproduce las reglas de notebooks/01_eda_obra.ipynb (secciones 1 a 13 y 17):
cruces de las fuentes, variable objetivo registrada, valor y plazo pactados,
muestra por fecha de firma y exclusiones por fuga.

Uso: python src/features.py  ->  data/processed/obra_modelo.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
SALIDA = RAIZ / "data" / "processed" / "obra_modelo.csv"
FECHA_DESCARGA = pd.Timestamp("2026-11-07")
UNIDADES = {"D": 1, "S": 7, "M": 30, "A": 365, "H": 1 / 24}
NO_DEFINIDO = {"", "nan", "no definido", "no definida", "no aplica",
               "sin descripcion"}
MODALIDADES = {
    "Selección Abreviada de Menor Cuantía": "Menor cuantía",
    "Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes":
        "Menor cuantía",
    "Contratación directa": "Directa",
    "Contratación Directa (con ofertas)": "Directa",
    "Mínima cuantía": "Mínima cuantía",
    "Licitación pública Obra Publica": "Licitación pública",
    "Licitación pública": "Licitación pública",
    "Contratación régimen especial": "Régimen especial",
    "Contratación régimen especial (con ofertas)": "Régimen especial",
}
FUENTES = {
    "presupuesto_general_de_la_nacion_pgn": "PGN",
    "sistema_general_de_participaciones": "SGP",
    "sistema_general_de_regal_as": "Regalías",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_":
        "Propios territoriales",
    "recursos_de_credito": "Crédito",
    "recursos_propios": "Propios",
}

SUAVIZADO = 20  # peso, en contratos, de la tasa global en la de la entidad
OBJETIVOS = ["y", "y_tiempo", "y_valor"]
NUMERICAS = [
    "log_valor_inicial", "plazo_inicial", "respuestas",
    "inicial_sobre_base", "dias_publicacion_adjudicacion",
    "tasa_entidad", "previos_entidad", "antiguedad_prov",
    "proceso_compartido", "proveedor_repetido",
]
CATEGORICAS = [
    "modalidad", "departamento", "segmento_unspsc", "fuente_principal",
    "destino_gasto", "condiciones_de_entrega", "es_pyme",
    "tipodocproveedor", "mes",
]
VARIABLES = NUMERICAS + CATEGORICAS
TEXTO = ["nombre_entidad"] + CATEGORICAS


def fecha(serie):
    """Convierte fechas de SECOP a datetime; las inválidas quedan en NaT."""
    return pd.to_datetime(serie.astype(str).str[:19], errors="coerce",
                          format="ISO8601")


def numero(serie):
    return pd.to_numeric(serie, errors="coerce")


def dias(cantidad, unidad):
    """Convierte una duración con unidad en texto (Dia(s), Mes(es)) a días."""
    return numero(cantidad) * unidad.str.strip().str[0].str.upper().map(
        UNIDADES)


def a_texto(serie):
    """Categórica como texto; los faltantes quedan como NaN."""
    return serie.map(lambda v: v if pd.isna(v) else str(v)).astype(object)


def limpiar(serie):
    """Texto sin "No definido" ni equivalentes, que pasan a NaN."""
    texto = serie.astype(str).str.strip()
    return serie.where(~texto.str.lower().isin(NO_DEFINIDO))


def previos(firma, grupos):
    """Contratos del mismo grupo firmados en días anteriores (sin empates)."""
    dia = firma.dt.normalize()
    return dia.groupby(grupos).rank(method="min") - 1


def tasa_suavizada(historia):
    """Tasa de adición por entidad, suavizada hacia la tasa de `historia`."""
    prior = historia["y"].mean()
    g = historia.groupby("nombre_entidad")["y"].agg(["sum", "count"])
    return (g["sum"] + SUAVIZADO * prior) / (g["count"] + SUAVIZADO), prior


def tasa_entidad(df):
    """Tasa suavizada de la entidad calculada solo con años anteriores.

    Reemplaza la codificación por tasa con pliegues aleatorios, que usaba
    desenlaces futuros de la misma entidad dentro del entrenamiento. Los
    contratos de 2019 no tienen historia y quedan como faltantes.
    """
    salida = pd.Series(np.nan, index=df.index)
    for anio in df["anio"].unique():
        historia = df[df["anio"] < anio]
        if historia.empty:
            continue
        tasas, prior = tasa_suavizada(historia)
        fila = df["anio"] == anio
        salida[fila] = df.loc[fila, "nombre_entidad"].map(tasas).fillna(prior)
    return salida


def cruzar(raw):
    """Une las cinco fuentes sobre Contratos (sección 1 del EDA)."""
    contratos = pd.read_csv(raw / "contratos_obra.csv", low_memory=False,
                            dtype={"codigo_proveedor": str})
    procesos = pd.read_csv(raw / "procesos_obra.csv", low_memory=False)
    ofertas = pd.read_csv(raw / "ofertas_obra.csv",
                          dtype={"c_digo_proveedor": str})
    proveedores = pd.read_csv(raw / "proveedores_obra.csv", low_memory=False,
                              dtype={"codigo": str})
    adiciones = pd.read_csv(raw / "adiciones_valor.csv")

    contratos = contratos.drop_duplicates("id_contrato")
    procesos["adjudicado_si"] = procesos["adjudicado"].eq("Si")
    procesos["publicacion"] = fecha(procesos["fecha_de_publicacion_del"])
    proc = (procesos.sort_values(["adjudicado_si", "publicacion"],
                                 ascending=False)
            .drop_duplicates("id_del_portafolio"))
    prov = proveedores.drop_duplicates("codigo").add_prefix("prov_")
    llave = ["id_del_proceso_de_compra", "c_digo_proveedor"]
    ofertas = ofertas.groupby(llave, as_index=False).agg(
        valor_oferta=("valor_oferta", "max"))
    ganadora = ofertas.rename(columns={"valor_oferta": "oferta_ganadora"})

    df = (contratos
          .merge(proc, how="left", left_on="proceso_de_compra",
                 right_on="id_del_portafolio", validate="m:1")
          .merge(prov, how="left", left_on="codigo_proveedor",
                 right_on="prov_codigo", validate="m:1")
          .merge(ganadora, how="left",
                 left_on=["proceso_de_compra", "codigo_proveedor"],
                 right_on=llave, validate="m:1"))
    df["y_valor"] = df["id_contrato"].isin(
        adiciones["id_contrato"]).astype(int)
    return df


def construir(raw=RAW):
    """Tabla de modelado con identificadores, objetivos y variables."""
    df = cruzar(raw)
    df["firma"] = fecha(df["fecha_de_firma"])
    df = df.sort_values(["firma", "id_contrato"], ignore_index=True)
    df["anio"] = df["firma"].dt.year
    df["mes"] = df["firma"].dt.month

    # Objetivo registrado (sección 2)
    df["dias_adic"] = numero(df["dias_adicionados"]).fillna(0)
    df["y_tiempo"] = (df["dias_adic"] > 0).astype(int)
    df["y"] = df[["y_valor", "y_tiempo"]].max(axis=1)

    # Valor y plazo pactados al firmar (sección 3)
    plazo = dias(df["duracion"], df["unidad_de_duracion"].astype(str))
    df["plazo_inicial"] = plazo.where(plazo.between(1, 3650))
    precio_base = numero(df["precio_base"])
    precio_base = precio_base.where(precio_base > 0)
    adjudicado = numero(df["valor_total_adjudicacion"])
    adjudicado = adjudicado.where((adjudicado > 0)
                                  & ~(adjudicado > 10 * precio_base))
    oferta = df["oferta_ganadora"]
    oferta = oferta.where((oferta > 0) & ~(oferta > 10 * precio_base))
    df["valor_inicial"] = adjudicado.fillna(oferta).fillna(precio_base)
    df["log_valor_inicial"] = np.log10(df["valor_inicial"])
    df["inicial_sobre_base"] = (df["valor_inicial"] / precio_base).where(
        adjudicado.notna() | oferta.notna())
    # Lote: otro contrato del mismo proceso firmado ese día o antes
    dia = df["firma"].dt.normalize()
    df["proceso_compartido"] = (dia.groupby(df["proceso_de_compra"])
                                .rank(method="max") > 1).astype(int)

    # Entidad, proveedor y competencia (secciones 10 y 12). Se cuentan antes
    # de excluir los vigentes: también son experiencia previa al firmar.
    df["previos_entidad"] = previos(df["firma"], df["nombre_entidad"])
    repetidos = previos(df["firma"], [df["nombre_entidad"],
                                      df["codigo_proveedor"]])
    df["proveedor_repetido"] = (repetidos > 0).astype(int)
    df["antiguedad_prov"] = (df["firma"] - fecha(df["prov_fecha_creacion"])
                             ).dt.days / 365.25
    df["respuestas"] = numero(df["respuestas_al_procedimiento"])

    # Objeto, financiación y tiempos del proceso (sección 13)
    df["segmento_unspsc"] = df["codigo_de_categoria_principal"].str.extract(
        r"V1\.(\d{2})")[0]
    montos = df[list(FUENTES)].apply(numero).fillna(0).rename(
        columns=FUENTES)
    df["fuente_principal"] = montos.idxmax(axis=1).where(
        montos.sum(axis=1) > 0)
    adjudicacion = fecha(df["fecha_adjudicacion"])
    df["dias_publicacion_adjudicacion"] = (
        adjudicacion - df["publicacion"]).dt.days.where(
            adjudicacion.dt.normalize() <= dia)  # adjudicar tras firmar: error
    df["modalidad"] = df["modalidad_de_contratacion"].map(MODALIDADES)

    for c in ["departamento", "destino_gasto", "condiciones_de_entrega",
              "es_pyme", "tipodocproveedor"]:
        df[c] = limpiar(df[c])
    for c in TEXTO:
        df[c] = a_texto(df[c])

    # Muestra: se excluyen los contratos con plazo inicial vigente (sección 4)
    inicio = fecha(df["fecha_de_inicio_del_contrato"])
    fin_pactado = inicio.fillna(df["firma"]) + pd.to_timedelta(
        df["plazo_inicial"], unit="D")
    df = df[~(fin_pactado >= FECHA_DESCARGA)].copy()
    df["tasa_entidad"] = tasa_entidad(df)

    # estado_contrato es posterior a la firma: solo para diagnóstico
    columnas = (["id_contrato", "proceso_de_compra", "firma", "anio",
                 "nombre_entidad", "valor_inicial", "dias_adic",
                 "estado_contrato"] + OBJETIVOS + VARIABLES)
    return df[columnas].reset_index(drop=True)


def cargar(ruta=SALIDA):
    """Lee la tabla procesada con las categóricas como texto."""
    return pd.read_csv(ruta, dtype={c: str for c in TEXTO},
                       parse_dates=["firma"])


if __name__ == "__main__":
    tabla = construir()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(SALIDA, index=False)
    print(f"{len(tabla):,} contratos -> {SALIDA.relative_to(RAIZ)}")
    print(tabla.groupby("anio")[OBJETIVOS].agg(["size", "mean"])
          .round(3).to_string())
