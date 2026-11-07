"""Modelos de riesgo de adición: entrenamiento, evaluación y predicción.

No depende de MLflow: `entrenar` devuelve el pipeline y un diccionario de
métricas, listos para mlflow.log_params, mlflow.log_metrics y log_model.

Uso:
    python src/modelo.py --modelo lightgbm --objetivo y
    python src/modelo.py --modelo catboost --param depth=8 --excluir mes
    python src/modelo.py --modelo lightgbm --final --guardar
"""
import argparse
import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
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
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

from features import (CATEGORICAS, ENTIDAD, NUMERICAS, OBJETIVOS, RAIZ,
                      VARIABLES, a_texto, cargar)

MODELOS_DIR = RAIZ / "models"
SEMILLA = 42
FIN_ENTRENA, VALIDA, PRUEBA = 2023, 2024, 2025
MODELOS = ["logistica", "random_forest", "lightgbm", "catboost"]
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

    1. Numéricas: mediana, indicador de faltante y escala estándar.
    2. Entidad: tasa de adición suavizada con validación cruzada interna.
    3. Categóricas: one-hot; categorías con menos de 50 contratos se agrupan.
    """
    def usar(lista):
        return [v for v in lista if v not in excluir]

    prep = ColumnTransformer([
        ("num", make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler()), usar(NUMERICAS)),
        ("ent", TargetEncoder(random_state=SEMILLA), usar(ENTIDAD)),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                              min_frequency=50, sparse_output=False),
         usar(CATEGORICAS)),
    ])
    pipe = Pipeline([("prep", prep), ("clf", clasificador(modelo))])
    return pipe.set_params(
        **{f"clf__{k}": v for k, v in (params or {}).items()})


def evaluar(y, p):
    """Métricas de priorización: PR-AUC, precisión en k, AUC y Brier."""
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
             final=False, datos=None):
    """Entrena con 2019-2023 y evalúa en 2024.

    Con final=True entrena con 2019-2024 y evalúa en 2025 (prueba).
    Devuelve el pipeline ajustado y las métricas del año evaluado.
    """
    datos = cargar() if datos is None else datos
    hasta, evalua = (VALIDA, PRUEBA) if final else (FIN_ENTRENA, VALIDA)
    tr = datos[datos["anio"] <= hasta]
    te = datos[datos["anio"] == evalua]
    pipe = pipeline(modelo, params, excluir)
    pipe.fit(tr[VARIABLES], tr[objetivo])
    p = pipe.predict_proba(te[VARIABLES])[:, 1]
    return pipe, evaluar(te[objetivo], p)


def buscar(modelo, objetivo="y", datos=None):
    """Búsqueda corta en REJILLAS, ordenada por PR-AUC en 2024."""
    datos = cargar() if datos is None else datos
    filas = [{**params, **entrenar(modelo, objetivo, params,
                                   datos=datos)[1]}
             for params in ParameterGrid(REJILLAS[modelo])]
    return pd.DataFrame(filas).sort_values("pr_auc", ascending=False)


def guardar(pipe, objetivo="y"):
    MODELOS_DIR.mkdir(exist_ok=True)
    ruta = MODELOS_DIR / f"modelo_{objetivo}.joblib"
    joblib.dump(pipe, ruta)
    return ruta


@lru_cache
def _modelo_guardado(objetivo):
    return joblib.load(MODELOS_DIR / f"modelo_{objetivo}.joblib")


def predecir(registros, objetivo="y"):
    """Probabilidad de adición para un contrato (dict) o varios (DataFrame).

    Las variables ausentes se tratan como faltantes. Si llega valor_inicial
    en pesos y no su logaritmo, se calcula aquí.
    """
    if isinstance(registros, dict):
        registros = [registros]
    X = pd.DataFrame(registros)
    if "log_valor_inicial" not in X and "valor_inicial" in X:
        X["log_valor_inicial"] = np.log10(
            pd.to_numeric(X["valor_inicial"], errors="coerce"))
    X = X.reindex(columns=VARIABLES)
    X[NUMERICAS] = X[NUMERICAS].apply(pd.to_numeric, errors="coerce")
    for c in ENTIDAD + CATEGORICAS:
        X[c] = a_texto(X[c])
    return _modelo_guardado(objetivo).predict_proba(X)[:, 1]


def _valor(texto):
    """Convierte '0.1', '63' o 'null' a número o None; si no, deja texto."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Entrena y evalúa un modelo.")
    a.add_argument("--modelo", choices=MODELOS, default="lightgbm")
    a.add_argument("--objetivo", choices=OBJETIVOS, default="y")
    a.add_argument("--param", action="append", default=[],
                   metavar="CLAVE=VALOR", help="hiperparámetro, repetible")
    a.add_argument("--excluir", nargs="*", default=[], metavar="VARIABLE")
    a.add_argument("--final", action="store_true",
                   help="entrena 2019-2024 y evalúa en 2025")
    a.add_argument("--guardar", action="store_true",
                   help="guarda el pipeline en models/")
    args = a.parse_args()
    params = dict(p.split("=", 1) for p in args.param)
    params = {k: _valor(v) for k, v in params.items()}
    pipe, metricas = entrenar(args.modelo, args.objetivo, params,
                              args.excluir, args.final)
    print(json.dumps(metricas, indent=2))
    if args.guardar:
        print("Guardado en", guardar(pipe, args.objetivo))
