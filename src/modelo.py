"""Modelos de riesgo de adición: entrenamiento, evaluación y predicción.

No depende de MLflow: `entrenar` devuelve el pipeline y un diccionario de
métricas, listos para mlflow.log_params, mlflow.log_metrics y log_model.

Uso:
    python src/modelo.py --modelo lightgbm --objetivo y
    python src/modelo.py --modelo catboost --param depth=8 --excluir mes
    python src/modelo.py --modelo logistica --param C=0.01 --validar
    python src/modelo.py --modelo lightgbm --evalua 2025 --guardar
    python src/modelo.py --ganador
"""
import argparse
import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             roc_auc_score)
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from features import (CATEGORICAS, NUMERICAS, OBJETIVOS, RAIZ, VARIABLES,
                      a_texto, cargar, tasa_suavizada)

MODELOS_DIR = RAIZ / "models"
SEMILLA = 42
PLIEGUES = [2022, 2023, 2024]  # validación con ventana creciente
PRUEBA = 2025
MODELOS = ["logistica", "random_forest", "lightgbm", "catboost"]
# Regla: mayor PR-AUC medio en PLIEGUES. Se excluyen fuente_principal por
# riesgo de fuga (sus montos se actualizan con las adiciones) y las variables
# sin aporte cuya salida baja el PR-AUC medio menos de 0,005. Se confirma
# con las corridas de MLflow; si cambia, se edita y se corre --ganador.
GANADOR = {"modelo": "catboost",
           "params": {"depth": 8, "learning_rate": 0.03},
           "excluir": ["fuente_principal", "proveedor_repetido",
                       "tipodocproveedor", "proceso_compartido"]}
REJILLAS = {
    "logistica": {"C": [0.01, 0.1, 1, 10]},
    "random_forest": {"min_samples_leaf": [5, 20, 50],
                      "max_features": ["sqrt", 0.3]},
    "lightgbm": {"num_leaves": [15, 31, 63], "learning_rate": [0.03, 0.1]},
    "catboost": {"depth": [4, 6, 8], "learning_rate": [0.03, 0.1]},
}


def clasificador(nombre):
    """Clasificador base con hiperparámetros iniciales razonables."""
    return {
        "logistica": LogisticRegression(max_iter=2000),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=20, n_jobs=-1,
            random_state=SEMILLA),
        "lightgbm": LGBMClassifier(
            n_estimators=400, learning_rate=0.05, num_leaves=31,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
            random_state=SEMILLA, verbose=-1),
        "catboost": CatBoostClassifier(
            iterations=500, learning_rate=0.05, depth=6,
            random_seed=SEMILLA, verbose=0, allow_writing_files=False),
    }[nombre]


def pipeline(modelo, params=None, excluir=()):
    """Preprocesamiento común a los cuatro modelos más el clasificador.

    1. Numéricas, incluida la tasa temporal de la entidad: mediana,
       indicador de faltante y escala estándar.
    2. Categóricas: one-hot; categorías con menos de 50 contratos se agrupan.
    """
    def usar(lista):
        return [v for v in lista if v not in excluir]

    prep = ColumnTransformer([
        ("num", make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler()), usar(NUMERICAS)),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                              min_frequency=50, sparse_output=False),
         usar(CATEGORICAS)),
    ])
    pipe = Pipeline([("prep", prep), ("clf", clasificador(modelo))])
    return pipe.set_params(
        **{f"clf__{k}": v for k, v in (params or {}).items()})


def evaluar(y, p):
    """Métricas de priorización: PR-AUC, precisión en k, AUC y Brier.

    Con menos de 100 contratos, precision_100 es la tasa del conjunto.
    """
    y, p = np.asarray(y), np.asarray(p)
    orden = y[np.argsort(-p, kind="stable")]
    k10 = max(1, round(0.1 * len(y)))
    return {
        "pr_auc": average_precision_score(y, p),
        "roc_auc": roc_auc_score(y, p),
        "brier": brier_score_loss(y, p),
        "precision_100": orden[:100].mean(),
        "precision_10pct": orden[:k10].mean(),
        "recall_10pct": orden[:k10].sum() / y.sum(),
        "lift_10pct": orden[:k10].mean() / y.mean(),
        "tasa_base": y.mean(),
    }


def entrenar(modelo="lightgbm", objetivo="y", params=None, excluir=(),
             evalua=2024, datos=None):
    """Entrena con los años anteriores a `evalua` y evalúa en ese año.

    evalua=2025 es la prueba final: entrena con 2019-2024.
    Devuelve el pipeline ajustado y las métricas del año evaluado.
    """
    datos = cargar() if datos is None else datos
    tr = datos[datos["anio"] < evalua]
    te = datos[datos["anio"] == evalua]
    pipe = pipeline(modelo, params, excluir)
    pipe.fit(tr[VARIABLES], tr[objetivo])
    p = pipe.predict_proba(te[VARIABLES])[:, 1]
    return pipe, evaluar(te[objetivo], p)


def validar(modelo="lightgbm", objetivo="y", params=None, excluir=(),
            datos=None):
    """Validación temporal con ventana creciente: métricas por pliegue."""
    datos = cargar() if datos is None else datos
    return pd.DataFrame(
        [entrenar(modelo, objetivo, params, excluir, a, datos)[1]
         for a in PLIEGUES], index=pd.Index(PLIEGUES, name="evalua"))


def buscar(modelo, objetivo="y", excluir=(), datos=None):
    """Búsqueda corta en REJILLAS, ordenada por PR-AUC medio en PLIEGUES."""
    datos = cargar() if datos is None else datos
    filas = []
    for params in ParameterGrid(REJILLAS[modelo]):
        m = validar(modelo, objetivo, params, excluir, datos)
        filas.append({**params, "params": params, **m.mean(),
                      "pr_auc_std": m["pr_auc"].std()})
    return pd.DataFrame(filas).sort_values("pr_auc", ascending=False)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibrar(modelo, objetivo="y", params=None, excluir=(), datos=None):
    """Coeficientes de Platt (a, b) ajustados en 2024 fuera de muestra.

    Un modelo entrenado con 2019-2023 predice 2024 y se ajusta
    y ~ sigmoide(a * logit(p) + b). El orden de los contratos no cambia.
    """
    datos = cargar() if datos is None else datos
    anio = PRUEBA - 1
    pipe, _ = entrenar(modelo, objetivo, params, excluir, anio, datos)
    te = datos[datos["anio"] == anio]
    z = _logit(pipe.predict_proba(te[VARIABLES])[:, 1]).reshape(-1, 1)
    platt = LogisticRegression(C=1e6).fit(z, te[objetivo])
    return float(platt.coef_[0, 0]), float(platt.intercept_[0])


def recalibrar(p, platt):
    a, b = platt
    return 1 / (1 + np.exp(-(a * _logit(p) + b)))


def guardar(pipe, objetivo="y", platt=None):
    MODELOS_DIR.mkdir(exist_ok=True)
    ruta = MODELOS_DIR / f"modelo_{objetivo}.joblib"
    joblib.dump({"pipeline": pipe, "platt": platt}, ruta)
    return ruta


@lru_cache
def _modelo_guardado(objetivo):
    return joblib.load(MODELOS_DIR / f"modelo_{objetivo}.joblib")


@lru_cache
def _tasas_actuales():
    """Tasa suavizada de cada entidad con toda la historia de la tabla."""
    return tasa_suavizada(cargar())


def preparar(registros):
    """Registros (dict o DataFrame) con las columnas y tipos del modelo.

    1. Las variables ausentes quedan como faltantes.
    2. Si llega valor_inicial en pesos y no su logaritmo, se calcula.
    3. Si llega nombre_entidad y no tasa_entidad, se toma la tasa de la
       entidad con toda la historia de data/processed/obra_modelo.csv.
    """
    if isinstance(registros, dict):
        registros = [registros]
    X = pd.DataFrame(registros)
    if "log_valor_inicial" not in X and "valor_inicial" in X:
        X["log_valor_inicial"] = np.log10(
            pd.to_numeric(X["valor_inicial"], errors="coerce"))
    if "tasa_entidad" not in X and "nombre_entidad" in X:
        tasas, prior = _tasas_actuales()
        X["tasa_entidad"] = X["nombre_entidad"].map(tasas).fillna(prior)
    X = X.reindex(columns=VARIABLES)
    X[NUMERICAS] = X[NUMERICAS].apply(pd.to_numeric, errors="coerce")
    for c in CATEGORICAS:
        X[c] = a_texto(X[c])
    return X


def predecir(registros, objetivo="y", calibrada=True):
    """Probabilidad de adición para un contrato (dict) o varios.

    Con calibrada=True aplica la recalibración de Platt guardada.
    """
    guardado = _modelo_guardado(objetivo)
    p = guardado["pipeline"].predict_proba(preparar(registros))[:, 1]
    if calibrada and guardado["platt"]:
        p = recalibrar(p, guardado["platt"])
    return p


def _variable_original(columna):
    """'cat__modalidad_Directa' -> 'modalidad'."""
    base = columna.split("__", 1)[1].removeprefix("missingindicator_")
    return next(v for v in VARIABLES
                if base == v or base.startswith(v + "_"))


def aportes(pipe, X, fondo):
    """Valores SHAP por contrato agrupados por variable original.

    `fondo` es una muestra de contratos de referencia (100 a 500 filas).
    Los aportes están en log-odds del modelo sin recalibrar; el signo indica
    si la variable sube o baja el riesgo.
    """
    prep, clf = pipe["prep"], pipe["clf"]
    explicador = shap.Explainer(clf, prep.transform(preparar(fondo)))
    valores = explicador(prep.transform(preparar(X))).values
    if valores.ndim == 3:  # una columna por clase: se toma la clase 1
        valores = valores[..., 1]
    columnas = [_variable_original(c) for c in prep.get_feature_names_out()]
    return pd.DataFrame(valores, columns=columnas).T.groupby(level=0).sum().T


def explicar(registro, fondo, objetivo="y", n=5):
    """Las n variables que más mueven el riesgo de un contrato (panel I)."""
    pipe = _modelo_guardado(objetivo)["pipeline"]
    a = aportes(pipe, registro, fondo).iloc[0]
    return a.reindex(a.abs().sort_values(ascending=False).index[:n])


def _valor(texto):
    """Convierte '0.1', '63' o 'null' a número o None; si no, deja texto."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Entrena y evalúa un modelo.")
    a.add_argument("--modelo", choices=MODELOS, default=GANADOR["modelo"])
    a.add_argument("--objetivo", choices=OBJETIVOS, default="y")
    a.add_argument("--param", action="append", default=[],
                   metavar="CLAVE=VALOR", help="hiperparámetro, repetible")
    a.add_argument("--excluir", nargs="*", default=[], metavar="VARIABLE")
    a.add_argument("--evalua", type=int, default=2024,
                   help="año evaluado; 2025 entrena con 2019-2024 (prueba)")
    a.add_argument("--validar", action="store_true",
                   help="métricas por pliegue temporal (2022 a 2024)")
    a.add_argument("--guardar", action="store_true",
                   help="guarda el pipeline en models/")
    a.add_argument("--ganador", action="store_true",
                   help="entrena GANADOR con 2019-2024 para los tres "
                        "objetivos, lo recalibra, evalúa en 2025 y lo guarda")
    args = a.parse_args()
    if args.ganador:
        datos = cargar()
        g = dict(modelo=GANADOR["modelo"], params=GANADOR["params"],
                 excluir=GANADOR["excluir"], datos=datos)
        for obj in OBJETIVOS:
            pipe, metricas = entrenar(objetivo=obj, evalua=PRUEBA, **g)
            platt = calibrar(objetivo=obj, **g)
            prueba = datos[datos["anio"] == PRUEBA]
            p = recalibrar(pipe.predict_proba(prueba[VARIABLES])[:, 1],
                           platt)
            metricas["brier_recalibrado"] = brier_score_loss(prueba[obj], p)
            print(obj, json.dumps(metricas, indent=2))
            print("Guardado en", guardar(pipe, obj, platt))
        raise SystemExit
    params = dict(p.split("=", 1) for p in args.param)
    params = {k: _valor(v) for k, v in params.items()}
    if args.validar:
        m = validar(args.modelo, args.objetivo, params, args.excluir)
        print(m.round(4).to_string())
        print(m.mean().round(4).to_string())
        raise SystemExit
    pipe, metricas = entrenar(args.modelo, args.objetivo, params,
                              args.excluir, args.evalua)
    print(json.dumps(metricas, indent=2))
    if args.guardar:
        print("Guardado en", guardar(pipe, args.objetivo))
