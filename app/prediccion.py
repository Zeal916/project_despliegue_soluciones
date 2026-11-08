import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from features import OBJETIVOS, cargar  # noqa: E402
from modelo import PRUEBA, explicar, predecir, preparar  # noqa: E402

UMBRAL_ALTA = 0.90
UMBRAL_MEDIA = 0.70
TAMANO_FONDO = 300

ETIQUETAS = {
    "log_valor_inicial": "Valor inicial",
    "plazo_inicial": "Plazo inicial (días)",
    "respuestas": "Respuestas al proceso",
    "inicial_sobre_base": "Valor adjudicado / precio base",
    "dias_publicacion_adjudicacion": "Días de publicación a adjudicación",
    "tasa_entidad": "Tasa histórica de la entidad",
    "previos_entidad": "Contratos previos de la entidad",
    "antiguedad_prov": "Antigüedad del proveedor (años)",
    "proceso_compartido": "Proceso compartido",
    "proveedor_repetido": "Proveedor repetido",
    "modalidad": "Modalidad",
    "departamento": "Departamento",
    "segmento_unspsc": "Segmento UNSPSC",
    "fuente_principal": "Fuente principal",
    "destino_gasto": "Destino del gasto",
    "condiciones_de_entrega": "Condiciones de entrega",
    "es_pyme": "Pyme",
    "tipodocproveedor": "Tipo de documento del proveedor",
    "mes": "Mes de firma",
}


class ErrorModelo(Exception):
    pass


@st.cache_resource(show_spinner="Cargando los modelos…")
def contexto():
    """Distribución de referencia de 2025, fondo para SHAP y conteos."""
    try:
        tabla = cargar()
        prueba = tabla[tabla["anio"] == PRUEBA]
        referencia = {o: np.sort(predecir(prueba, o)) for o in OBJETIVOS}
    except FileNotFoundError as e:
        raise ErrorModelo(
            f"No se encontraron los modelos o la tabla ({e.filename}). "
            "Ejecute python src/features.py y python src/modelo.py "
            "--ganador.") from e
    entrenamiento = tabla[tabla["anio"] < PRUEBA]
    return {
        "referencia": referencia,
        "fondo": entrenamiento.sample(min(TAMANO_FONDO, len(entrenamiento)),
                                      random_state=42),
        "conteo_entidad": tabla["nombre_entidad"].value_counts(),
        "contratos_referencia": len(prueba),
    }


def estado() -> dict:
    try:
        ctx = contexto()
        return {"estado": "ok", "anio_referencia": PRUEBA,
                "contratos_referencia": ctx["contratos_referencia"]}
    except ErrorModelo as e:
        return {"estado": "error", "detalle": str(e)}


def _limpio(valor):
    if isinstance(valor, (np.floating, float)):
        return None if not math.isfinite(valor) else float(valor)
    if isinstance(valor, np.integer):
        return int(valor)
    return valor


def _nivel(percentil: float) -> str:
    if percentil >= UMBRAL_ALTA:
        return "alta"
    if percentil >= UMBRAL_MEDIA:
        return "media"
    return "baja"


def _completar(X: pd.DataFrame, conteo) -> pd.DataFrame:
    """Contratos previos de la entidad: si no llegan, se cuentan en la tabla
    (para un contrato que se firma hoy, toda la historia es previa). Una
    columna tasa_entidad presente, aun vacía, no se recalcula."""
    X = X.copy()
    if "nombre_entidad" in X:
        previos = X["nombre_entidad"].map(conteo).fillna(0)
        X["previos_entidad"] = (X["previos_entidad"].fillna(previos)
                                if "previos_entidad" in X else previos)
    return X


def _puntuar(X: pd.DataFrame, ctx):
    p = {o: predecir(X, o) for o in OBJETIVOS}
    pct = {o: np.searchsorted(ctx["referencia"][o], p[o], side="left")
           / len(ctx["referencia"][o]) for o in OBJETIVOS}
    total = np.max(np.vstack([p[o] for o in OBJETIVOS]), axis=0)
    return p, pct, total


def predecir_contrato(contrato: dict, n: int = 6) -> dict:
    """Probabilidades, percentiles, alerta y factores SHAP de un contrato."""
    ctx = contexto()
    datos = {k: v for k, v in contrato.items() if k != "id_contrato"}
    X = _completar(pd.DataFrame([datos]), ctx["conteo_entidad"])
    p, pct, total = _puntuar(X, ctx)
    preparado = preparar(X).iloc[0]
    salida = {
        "id_contrato": contrato.get("id_contrato"),
        "probabilidades": {o: float(p[o][0]) for o in OBJETIVOS},
        "percentiles": {o: float(pct[o][0]) for o in OBJETIVOS},
        "riesgo_total": float(total[0]),
        "percentil": float(pct["y"][0]),
        "nivel_alerta": _nivel(pct["y"][0]),
        "alerta": bool(pct["y"][0] >= UMBRAL_ALTA),
        "tasa_entidad_usada": _limpio(preparado["tasa_entidad"]),
        "entidad_con_historia": bool(
            contrato.get("nombre_entidad") in ctx["conteo_entidad"].index),
        "factores": {},
    }
    for o in OBJETIVOS:
        aporte = explicar(X, ctx["fondo"], o, n)
        salida["factores"][o] = [
            {"variable": v, "etiqueta": ETIQUETAS.get(v, v),
             "valor": _limpio(preparado[v]), "aporte": float(a)}
            for v, a in aporte.items()]
    return salida


def predecir_lote(registros: pd.DataFrame) -> pd.DataFrame:
    """Probabilidades, percentil y alerta para varios contratos (vista 3)."""
    ctx = contexto()
    X = _completar(registros.drop(columns="id_contrato", errors="ignore")
                   .reset_index(drop=True), ctx["conteo_entidad"])
    p, pct, total = _puntuar(X, ctx)
    return pd.DataFrame({
        "id_contrato": registros["id_contrato"].to_numpy(),
        "p_y": p["y"], "p_tiempo": p["y_tiempo"], "p_valor": p["y_valor"],
        "riesgo_total": total, "percentil": pct["y"],
        "nivel_alerta": [_nivel(x) for x in pct["y"]],
    })
