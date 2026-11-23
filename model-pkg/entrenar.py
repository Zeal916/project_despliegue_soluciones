"""Genera trained/artefactos.joblib del paquete a partir del repositorio.

Requiere la tabla y los modelos del modelo ganador:
    python src/features.py
    python src/modelo.py --ganador
    python model-pkg/entrenar.py

Al final comprueba que el paquete da las mismas probabilidades y factores
SHAP que src/modelo.py en contratos de 2025.
"""
import sys
from pathlib import Path

import joblib
import numpy as np

PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(PKG.parent / "src"))
from features import (CATEGORICAS, NUMERICAS, OBJETIVOS,  # noqa: E402
                      VARIABLES, cargar, tasa_suavizada)
from modelo import MODELOS_DIR, PRUEBA, explicar, predecir  # noqa: E402

TAMANO_FONDO = 300  # contratos de entrenamiento de referencia para SHAP
SALIDA = PKG / "secop_obra_modelo" / "trained" / "artefactos.joblib"


def generar():
    tabla = cargar()
    prueba = tabla[tabla["anio"] == PRUEBA]
    entrenamiento = tabla[tabla["anio"] < PRUEBA]
    tasas, prior = tasa_suavizada(tabla)
    fondo = entrenamiento.sample(min(TAMANO_FONDO, len(entrenamiento)),
                                 random_state=42)
    artefactos = {
        "numericas": NUMERICAS,
        "categoricas": CATEGORICAS,
        "modelos": {o: joblib.load(MODELOS_DIR / f"modelo_{o}.joblib")
                    for o in OBJETIVOS},
        "referencia": {o: np.sort(predecir(prueba, o)) for o in OBJETIVOS},
        "fondo": fondo[VARIABLES].reset_index(drop=True),
        "conteo_entidad": tabla["nombre_entidad"].value_counts().to_dict(),
        "tasas_entidad": tasas.to_dict(),
        "prior": float(prior),
        "anio_referencia": PRUEBA,
        "contratos_referencia": len(prueba),
    }
    SALIDA.parent.mkdir(exist_ok=True)
    joblib.dump(artefactos, SALIDA, compress=3)
    print(f"Guardado {SALIDA.relative_to(PKG)} "
          f"({SALIDA.stat().st_size / 1e6:.1f} MB)")
    return tabla, prueba, fondo


def comprobar(prueba, fondo):
    """Mismas probabilidades y factores que src/modelo.py."""
    sys.path.insert(0, str(PKG))
    from secop_obra_modelo import predecir_contrato, predecir_lote

    muestra = prueba.sample(200, random_state=0)
    registros = (muestra[["id_contrato"] + VARIABLES].astype(object)
                 .where(muestra[["id_contrato"] + VARIABLES].notna(), None)
                 .to_dict(orient="records"))
    lote = predecir_lote(registros)
    for o, campo in zip(OBJETIVOS, ["p_y", "p_tiempo", "p_valor"]):
        dif = np.abs(np.array([r[campo] for r in lote])
                     - predecir(muestra, o)).max()
        assert dif < 1e-9, f"{o}: diferencia {dif}"
    uno = predecir_contrato(registros[0])
    esperado = explicar(muestra.iloc[[0]], fondo, "y", 6)
    obtenido = {f["variable"]: f["aporte"] for f in uno["factores"]["y"]}
    assert list(obtenido) == list(esperado.index), (obtenido, esperado)
    assert np.allclose(list(obtenido.values()), esperado.to_numpy())
    print("Comprobación OK: probabilidades y factores SHAP coinciden con "
          "src/modelo.py en 200 contratos de 2025")


if __name__ == "__main__":
    _, prueba, fondo = generar()
    comprobar(prueba, fondo)
