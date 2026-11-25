# Experimentos en MLflow: resultados

Los experimentos se registran con `src/experimentos.py` en un servidor MLflow sobre EC2 (guía en `docs/mlflow_ec2.md`).
El servidor solo tiene instalado MLflow (`docker/ec2_mlflow.sh`): el script se ejecuta en el computador de un integrante,
que entrena los modelos con las funciones de `src/modelo.py` y envía al servidor los parámetros, las métricas y los
modelos. Cada corrida lleva la etiqueta `datos_md5`, que identifica la tabla de modelado generada con los datos de DVC.

## 1. Registros

| Registro | Fecha | Instancia | Experimentos | Corridas |
| --- | --- | --- | --- | --- |
| Entrega 2 | 8 de noviembre de 2026 | EC2 de MLflow de la segunda entrega | 1 a 5 | 35 |
| Entrega 3 | 23 de noviembre de 2026 | `dsa_mlflow` (`i-0ba9d5fb4b5ac1bb3`, `t3.small`, `us-east-1`) | 1 a 6 | 37 |

El registro de la Entrega 3 repite los experimentos 1 a 5 y agrega el 6. Como se calculó desde otro computador, sus
cifras difieren de las del registro de la Entrega 2 a lo sumo en la tercera cifra decimal. Las capturas están en las
figuras 1 a 3 del reporte de la Entrega 3.

## 2. Resultados del registro de la Entrega 3

| # | Experimento | Corridas | Resultado (PR-AUC medio de validación 2022 a 2024) |
| --- | --- | --- | --- |
| 1 | Modelos base | 4 | CatBoost 0,522; Random Forest 0,521; LightGBM 0,510; regresión logística 0,505 |
| 2 | Ajuste de hiperparámetros | 22 | Mejor por algoritmo: CatBoost 0,528; Random Forest 0,526; LightGBM 0,520; regresión logística 0,514 |
| 3 | Selección de variables | 4 | Todas 0,528; sin las 3 sin aporte 0,530; sin `fuente_principal` 0,523; final (15 variables) 0,525 |
| 4 | Objetivos | 2 | Adición en tiempo 0,487 (tasa base 0,253); en valor 0,217 (tasa base 0,094) |
| 5 | Prueba en 2025 | 3 | Tabla de la sección 4; los tres modelos quedan en el Model Registry |
| 6 | Ensamble | 2 | Ensamble 0,526 frente a 0,525 del modelo final; no se adopta |

## 3. Selección del modelo

1. En el registro de la Entrega 2, la regla (mayor PR-AUC medio de validación, sin usar 2025) eligió **CatBoost con
   `depth=8` y `learning_rate=0.03`** (0,5283), por encima de `depth=6` (0,5279). Esa configuración es el modelo
   vigente y está en `GANADOR` de `src/modelo.py`.
2. Una alternativa reemplaza al modelo vigente solo si sube el PR-AUC medio de validación en 0,005 o más, umbral fijado
   antes de evaluar alternativas.
3. En el registro de la Entrega 3, `depth=6` queda arriba con 0,52840 frente a 0,52834. La diferencia cambia de signo
   entre registros y es menor que una centésima de la desviación del PR-AUC entre años del modelo final (0,042). No
   alcanza el umbral y se conserva `depth=8`.
4. El ensamble (promedio en log-odds del modelo vigente y LightGBM con `num_leaves=15`) sube el PR-AUC medio de 0,5253 a
   0,5263 (+0,0010), por debajo del umbral, y con shap 0.51 la explicación de LightGBM no es aditiva (error de hasta
   0,165). No se adopta.
5. La precisión en el 10 % de mayor riesgo es la métrica secundaria: se reporta, pero no entra en la regla.

## 4. Prueba en 2025 (entrenamiento 2019 a 2024)

| Objetivo | Tasa base | PR-AUC | ROC-AUC | Precisión top 10 % | Lift top 10 % | Brier / recalibrado |
| --- | --- | --- | --- | --- | --- | --- |
| Adición (tiempo o valor) | 0,470 | 0,644 | 0,692 | 0,730 | 1,55 | 0,253 / 0,231 |
| Adición en tiempo | 0,425 | 0,614 | 0,708 | 0,677 | 1,59 | 0,256 / 0,228 |
| Adición en valor | 0,079 | 0,189 | 0,704 | 0,216 | 2,75 | 0,069 / 0,069 |

Los modelos registrados (`riesgo_adicion_y`, `riesgo_adicion_y_tiempo` y `riesgo_adicion_y_valor`, versión 1) guardan
el pipeline de scikit-learn con su firma de entrada y un ejemplo; los coeficientes de Platt quedan como parámetros de la
corrida. La API no carga los modelos desde MLflow: usa el paquete `secop_obra_modelo` (`model-pkg/`), entrenado con la
misma configuración, para no depender del servidor de MLflow, que queda detenido.
