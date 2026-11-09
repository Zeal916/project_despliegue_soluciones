"""Registra en MLflow los 5 experimentos de docs/modelos.md (35 corridas).

1. Modelos base: validar(m) para los cuatro modelos.
2. Ajuste de hiperparámetros: cada combinación de REJILLAS.
3. Selección de variables con la configuración ganadora de 1 y 2.
4. Objetivos y_tiempo e y_valor con la configuración final.
5. Prueba en 2025 de los tres objetivos; los modelos se registran en el
   Model Registry como riesgo_adicion_<objetivo>.

Cada corrida guarda la media de las métricas en 2022-2024, la desviación del
PR-AUC y la métrica de cada año con step = año.

Uso:
    MLFLOW_TRACKING_URI=http://<ip-ec2>:5000 python src/experimentos.py
    python src/experimentos.py --solo 1 2      # solo algunos experimentos
"""
import argparse
import hashlib

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import ParameterGrid

from features import OBJETIVOS, SALIDA, VARIABLES, cargar
from modelo import (GANADOR, MODELOS, PRUEBA, REJILLAS, calibrar, entrenar,
                    recalibrar, validar)

SIN_APORTE = ["proveedor_repetido", "tipodocproveedor", "proceso_compartido"]
PREFIJO = "secop_obra"


def registrar(nombre, experimento, modelo, objetivo="y", params=None,
              excluir=(), datos=None):
    """Una corrida de validación temporal; devuelve el PR-AUC medio."""
    mlflow.set_experiment(f"{PREFIJO}/{experimento}")
    with mlflow.start_run(run_name=nombre):
        mlflow.set_tags({"experimento": experimento, "datos_md5": MD5})
        mlflow.log_params({"modelo": modelo, "objetivo": objetivo,
                           "excluir": ",".join(excluir) or "ninguna",
                           "n_variables": len(VARIABLES) - len(excluir),
                           **(params or {})})
        m = validar(modelo, objetivo, params, list(excluir), datos)
        for anio, fila in m.iterrows():
            mlflow.log_metrics(fila.to_dict(), step=anio)
        mlflow.log_metrics({f"val_{k}": v for k, v in m.mean().items()})
        mlflow.log_metric("val_pr_auc_std", m["pr_auc"].std())
    print(f"{experimento:<22} {nombre:<40} PR-AUC {m['pr_auc'].mean():.4f}")
    return m["pr_auc"].mean()


def prueba(objetivo, params, excluir, datos):
    """Experimento 5: entrena 2019-2024, evalúa 2025 y registra el modelo."""
    mlflow.set_experiment(f"{PREFIJO}/5_prueba_2025")
    modelo = GANADOR["modelo"]
    with mlflow.start_run(run_name=f"{modelo}_{objetivo}"):
        mlflow.set_tags({"experimento": "5_prueba_2025", "datos_md5": MD5})
        pipe, metricas = entrenar(modelo, objetivo, params, excluir,
                                  PRUEBA, datos)
        a, b = calibrar(modelo, objetivo, params, excluir, datos)
        te = datos[datos["anio"] == PRUEBA]
        p = recalibrar(pipe.predict_proba(te[VARIABLES])[:, 1], (a, b))
        metricas["brier_recalibrado"] = brier_score_loss(te[objetivo], p)
        mlflow.log_params({"modelo": modelo, "objetivo": objetivo,
                           "excluir": ",".join(excluir), "platt_a": a,
                           "platt_b": b, "entrena": f"2019-{PRUEBA - 1}",
                           **params})
        mlflow.log_metrics({f"test_{k}": v for k, v in metricas.items()})
        ejemplo = te[VARIABLES].head(5)
        mlflow.sklearn.log_model(
            pipe, name="modelo", input_example=ejemplo,
            signature=infer_signature(ejemplo, pipe.predict_proba(ejemplo)),
            registered_model_name=f"riesgo_adicion_{objetivo}")
    print(f"5_prueba_2025          {objetivo:<40} PR-AUC "
          f"{metricas['pr_auc']:.4f}")


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--solo", type=int, nargs="*", default=[1, 2, 3, 4, 5])
    solo = a.parse_args().solo
    MD5 = hashlib.md5(SALIDA.read_bytes()).hexdigest()
    datos = cargar()
    print("Tracking:", mlflow.get_tracking_uri(), "| contratos:", len(datos))

    # 1 y 2: la configuración ganadora es la de mayor PR-AUC medio.
    # Si no se corren, se parte de GANADOR.
    candidatos = [(0, GANADOR["modelo"], GANADOR["params"])]
    if 1 in solo:
        for m in MODELOS:
            candidatos.append(
                (registrar(f"{m}_base", "1_modelos_base", m, datos=datos),
                 m, {}))
    if 2 in solo:
        for m in MODELOS:
            for params in ParameterGrid(REJILLAS[m]):
                nombre = m + "_" + "_".join(f"{k}={v}"
                                            for k, v in params.items())
                candidatos.append((registrar(nombre, "2_hiperparametros", m,
                                             params=params, datos=datos),
                                   m, params))
    _, modelo, params = max(candidatos, key=lambda c: c[0])
    coincide = (modelo, params) == (GANADOR["modelo"], GANADOR["params"])
    print(f"Ganador: {modelo} {params} -> "
          f"{'coincide con' if coincide else 'DIFIERE de'} GANADOR")

    if 3 in solo:
        for nombre, excluir in [
                ("todas", []), ("sin_variables_sin_aporte", SIN_APORTE),
                ("sin_fuente_principal", ["fuente_principal"]),
                ("final", GANADOR["excluir"])]:
            registrar(nombre, "3_seleccion_variables", modelo,
                      params=params, excluir=excluir, datos=datos)
    if 4 in solo:
        for obj in OBJETIVOS[1:]:
            registrar(f"{modelo}_{obj}", "4_objetivos", modelo, obj,
                      params, GANADOR["excluir"], datos)
    if 5 in solo:
        for obj in OBJETIVOS:
            prueba(obj, params, GANADOR["excluir"], datos)
