"""Riesgo de adición de contratos de obra de SECOP II al momento de la firma.

Funciones que consume la API del tablero:
1. estado(): disponibilidad de los modelos (GET /health).
2. predecir_contrato(contrato): probabilidades, percentiles, alerta y
   factores SHAP de un contrato (POST /predict).
3. predecir_lote(contratos): probabilidades, percentil y alerta de varios
   contratos (POST /predict/lote).

Los artefactos (tres modelos CatBoost recalibrados, probabilidades de
referencia de 2025, fondo para SHAP y tasas por entidad) están en
trained/artefactos.joblib y se generan con model-pkg/entrenar.py.
"""
import math
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from pydantic import BaseModel, ConfigDict

DIR = Path(__file__).resolve().parent
ARTEFACTOS = DIR / "trained" / "artefactos.joblib"
VERSION = (DIR / "VERSION").read_text().strip()
OBJETIVOS = ["y", "y_tiempo", "y_valor"]
UMBRAL_ALTA = 0.90  # percentil frente a 2025: 10 % de mayor riesgo
UMBRAL_MEDIA = 0.70
ETIQUETAS = {
    "log_valor_inicial": "Valor inicial",
    "plazo_inicial": "Plazo inicial (días)",
    "respuestas": "Respuestas al proceso",
    "inicial_sobre_base": "Valor adjudicado / precio base",
    "dias_publicacion_adjudicacion": "Días de publicación a adjudicación",
    "tasa_entidad": "Tasa histórica de la entidad",
    "previos_entidad": "Contratos previos de la entidad",
    "antiguedad_prov": "Antigüedad del proveedor (años)",
    "modalidad": "Modalidad",
    "departamento": "Departamento",
    "segmento_unspsc": "Segmento UNSPSC",
    "destino_gasto": "Destino del gasto",
    "condiciones_de_entrega": "Condiciones de entrega",
    "es_pyme": "Pyme",
    "mes": "Mes de firma",
}


class Contrato(BaseModel):
    """Variables conocidas al firmar. Todas son opcionales: un faltante se
    imputa en el modelo. Una tasa_entidad enviada vacía no se recalcula."""

    model_config = ConfigDict(extra="ignore", coerce_numbers_to_str=True)

    id_contrato: str | None = None
    valor_inicial: float | None = None
    log_valor_inicial: float | None = None
    plazo_inicial: float | None = None
    respuestas: float | None = None
    inicial_sobre_base: float | None = None
    dias_publicacion_adjudicacion: float | None = None
    nombre_entidad: str | None = None
    tasa_entidad: float | None = None
    previos_entidad: float | None = None
    antiguedad_prov: float | None = None
    modalidad: str | None = None
    departamento: str | None = None
    segmento_unspsc: str | None = None
    destino_gasto: str | None = None
    condiciones_de_entrega: str | None = None
    es_pyme: str | None = None
    mes: str | None = None


@lru_cache
def _artefactos():
    return joblib.load(ARTEFACTOS)


def _validar(registros):
    """Valida cada registro; conserva solo los campos que llegaron."""
    return pd.DataFrame([Contrato.model_validate(r)
                         .model_dump(exclude_unset=True) for r in registros])


def _preparar(X, a):
    """Columnas y tipos del modelo.

    1. Logaritmo del valor inicial si llega en pesos.
    2. Tasa de la entidad con toda la historia si no llega.
    3. Contratos previos de la entidad si no llegan.
    """
    X = X.copy()
    if "log_valor_inicial" not in X and "valor_inicial" in X:
        X["log_valor_inicial"] = np.log10(
            pd.to_numeric(X["valor_inicial"], errors="coerce"))
    if "nombre_entidad" in X:
        if "tasa_entidad" not in X:
            X["tasa_entidad"] = (X["nombre_entidad"]
                                 .map(a["tasas_entidad"]).fillna(a["prior"]))
        previos = X["nombre_entidad"].map(a["conteo_entidad"]).fillna(0)
        X["previos_entidad"] = (X["previos_entidad"].fillna(previos)
                                if "previos_entidad" in X else previos)
    X = X.reindex(columns=a["numericas"] + a["categoricas"])
    X[a["numericas"]] = X[a["numericas"]].apply(pd.to_numeric,
                                                errors="coerce")
    # Faltante como NaN, igual que en el entrenamiento: el one-hot trata
    # None y NaN como categorías distintas.
    for c in a["categoricas"]:
        X[c] = X[c].map(lambda v: np.nan if pd.isna(v) else str(v)
                        ).astype(object)
    return X


def _probabilidad(Xp, objetivo, a):
    """Probabilidad recalibrada con Platt (ajustado con 2024)."""
    m = a["modelos"][objetivo]
    p = np.clip(m["pipeline"].predict_proba(Xp)[:, 1], 1e-6, 1 - 1e-6)
    pa, pb = m["platt"]
    return 1 / (1 + np.exp(-(pa * np.log(p / (1 - p)) + pb)))


def _puntuar(Xp, a):
    p = {o: _probabilidad(Xp, o, a) for o in OBJETIVOS}
    pct = {o: np.searchsorted(a["referencia"][o], p[o], side="left")
           / len(a["referencia"][o]) for o in OBJETIVOS}
    total = np.max(np.vstack([p[o] for o in OBJETIVOS]), axis=0)
    return p, pct, total


@lru_cache
def _explicador(objetivo):
    a = _artefactos()
    pipe = a["modelos"][objetivo]["pipeline"]
    fondo = pipe["prep"].transform(_preparar(a["fondo"], a))
    return shap.Explainer(pipe["clf"], fondo)


def _variable_original(columna, variables):
    """'cat__modalidad_Directa' -> 'modalidad'."""
    base = columna.split("__", 1)[1].removeprefix("missingindicator_")
    return next(v for v in variables
                if base == v or base.startswith(v + "_"))


def _factores(Xp, objetivo, n, a):
    """Las n variables con mayor aporte SHAP (log-odds sin recalibrar)."""
    prep = a["modelos"][objetivo]["pipeline"]["prep"]
    valores = _explicador(objetivo)(prep.transform(Xp)).values
    if valores.ndim == 3:  # una columna por clase: se toma la clase 1
        valores = valores[..., 1]
    variables = a["numericas"] + a["categoricas"]
    columnas = [_variable_original(c, variables)
                for c in prep.get_feature_names_out()]
    aporte = pd.Series(valores[0], index=columnas).groupby(level=0).sum()
    return aporte.reindex(aporte.abs().sort_values(ascending=False).index[:n])


def _limpio(valor):
    if isinstance(valor, (np.floating, float)):
        return float(valor) if math.isfinite(valor) else None
    if isinstance(valor, np.integer):
        return int(valor)
    return valor


def _nivel(percentil):
    if percentil >= UMBRAL_ALTA:
        return "alta"
    return "media" if percentil >= UMBRAL_MEDIA else "baja"


def estado():
    """Disponibilidad de los modelos y año de referencia del percentil."""
    try:
        a = _artefactos()
    except FileNotFoundError:
        return {"estado": "error", "version": VERSION,
                "detalle": f"No se encontró {ARTEFACTOS.name}; "
                           "ejecute model-pkg/entrenar.py."}
    return {"estado": "ok", "version": VERSION,
            "anio_referencia": a["anio_referencia"],
            "contratos_referencia": a["contratos_referencia"]}


def predecir_contrato(contrato, factores=True, n=6):
    """Probabilidades, percentiles, alerta y factores SHAP de un contrato.

    Lanza pydantic.ValidationError si un campo tiene un tipo inválido.
    """
    a = _artefactos()
    X = _validar([contrato])
    id_contrato = X.pop("id_contrato")[0] if "id_contrato" in X else None
    Xp = _preparar(X, a)
    p, pct, total = _puntuar(Xp, a)
    entidad = contrato.get("nombre_entidad")
    salida = {
        "id_contrato": id_contrato,
        "probabilidades": {o: float(p[o][0]) for o in OBJETIVOS},
        "percentiles": {o: float(pct[o][0]) for o in OBJETIVOS},
        "riesgo_total": float(total[0]),
        "percentil": float(pct["y"][0]),
        "nivel_alerta": _nivel(pct["y"][0]),
        "alerta": bool(pct["y"][0] >= UMBRAL_ALTA),
        "tasa_entidad_usada": _limpio(Xp["tasa_entidad"].iloc[0]),
        "entidad_con_historia": entidad in a["conteo_entidad"],
        "factores": {},
    }
    if factores:
        fila = Xp.iloc[0]
        for o in OBJETIVOS:
            salida["factores"][o] = [
                {"variable": v, "etiqueta": ETIQUETAS.get(v, v),
                 "valor": _limpio(fila[v]), "aporte": float(ap)}
                for v, ap in _factores(Xp, o, n, a).items()]
    return salida


def predecir_lote(contratos):
    """Probabilidades, percentil y alerta de varios contratos."""
    if not contratos:
        return []
    a = _artefactos()
    X = _validar(contratos)
    ids = (X.pop("id_contrato") if "id_contrato" in X
           else pd.Series([None] * len(X)))
    p, pct, total = _puntuar(_preparar(X, a), a)
    return [{"id_contrato": _limpio(i), "p_y": float(py),
             "p_tiempo": float(pt), "p_valor": float(pv),
             "riesgo_total": float(r), "percentil": float(q),
             "nivel_alerta": _nivel(q)}
            for i, py, pt, pv, r, q in zip(
                ids, p["y"], p["y_tiempo"], p["y_valor"], total, pct["y"])]
