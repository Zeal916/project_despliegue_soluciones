# Borrador para el reporte: experimentos en MLflow

Cifras de las corridas registradas en el servidor MLflow de EC2 el 8 de noviembre de 2026, con la tabla de modelado
generada a partir de los datos versionados en DVC (etiqueta `datos_md5` de cada corrida).

Los experimentos se registraron con `src/experimentos.py` en un servidor MLflow 3.5 sobre EC2 (Ubuntu 24.04, SQLite como
almacén de metadatos y artefactos servidos por el mismo servidor). Cada corrida guarda el modelo, el objetivo, los
hiperparámetros y las variables excluidas como parámetros; como métricas, el PR-AUC, ROC-AUC, Brier, precisión y
exhaustividad en el 10 % de mayor riesgo por año de validación (2022, 2023 y 2024, con step = año), su media y la
desviación del PR-AUC. Son 5 experimentos y 35 corridas:

| # | Experimento | Corridas | Resultado (PR-AUC medio de validación) |
| --- | --- | --- | --- |
| 1 | Modelos base | 4 | Random Forest y CatBoost empatan (0,522); LightGBM 0,510; logística 0,505 |
| 2 | Ajuste de hiperparámetros | 22 | Mejor por modelo: CatBoost 0,528, Random Forest 0,526, LightGBM 0,520, logística 0,514 |
| 3 | Selección de variables | 4 | Todas 0,528; sin las 3 sin aporte 0,530; además sin `fuente_principal` (final, 15 variables) 0,525 |
| 4 | Objetivos | 2 | Adición en tiempo 0,486; en valor 0,218 (tasa base cercana a 8 %) |
| 5 | Prueba en 2025 | 3 | Ver tabla siguiente; los tres modelos quedan en el Model Registry |

La regla de selección (mayor PR-AUC medio de validación, sin usar 2025) elige **CatBoost con `depth=8` y
`learning_rate=0.03`** (0,5283), apenas por encima de `depth=6` (0,5279). La diferencia es mucho menor que la variación
entre años, así que en la práctica es un empate; se respeta la regla fijada antes de ver los resultados. Las
diferencias entre los cuatro algoritmos son pequeñas (0,514 a 0,528) y la tasa de aprendizaje pesa más que el algoritmo:
con 0,1 los modelos de árboles bajan a 0,495-0,511. Quitar las 3 variables sin aporte no empeora el modelo (sube a
0,530); quitar `fuente_principal` cuesta 0,004, pero se excluye por riesgo de fuga.

Prueba en 2025 (entrenamiento 2019-2024):

| Objetivo | Tasa base | PR-AUC | ROC-AUC | Precisión top 10 % | Lift top 10 % | Brier / recalibrado |
| --- | --- | --- | --- | --- | --- | --- |
| Adición (tiempo o valor) | 0,470 | 0,644 | 0,692 | 0,730 | 1,55 | 0,253 / 0,231 |
| Adición en tiempo | 0,425 | 0,614 | 0,708 | 0,677 | 1,59 | 0,256 / 0,228 |
| Adición en valor | 0,079 | 0,189 | 0,704 | 0,216 | 2,75 | 0,069 / 0,069 |

Los modelos registrados (`riesgo_adicion_y`, `riesgo_adicion_y_tiempo`, `riesgo_adicion_y_valor`, versión 1) guardan el
pipeline de scikit-learn con su firma de entrada y un ejemplo; la API de la entrega 3 los puede cargar con
`mlflow.sklearn.load_model("models:/riesgo_adicion_y/1")`. Los coeficientes de Platt quedan como parámetros de la corrida.
