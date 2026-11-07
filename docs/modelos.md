# Modelos: guía de uso para MLflow y el tablero

Código: `src/features.py` (tabla de modelado) y `src/modelo.py` (modelos). Resultados: `notebooks/02_modelos.ipynb`.

## 1. Entorno y datos

1. Instalar el entorno (Python 3.11): `pip install -r requirements-eda.txt`.
2. Descargar los datos crudos: `dvc pull`.
3. Generar la tabla de modelado: `python src/features.py`. Escribe `data/processed/obra_modelo.csv` (40.170
   contratos, fuera de Git).
4. Guardar los modelos seleccionados: `python src/modelo.py --ganador`. Escribe `models/modelo_y.joblib`,
   `models/modelo_y_tiempo.joblib` y `models/modelo_y_valor.joblib` (fuera de Git).

## 2. Funciones de `src/modelo.py`

| Función | Qué hace | Devuelve |
| --- | --- | --- |
| `entrenar(modelo, objetivo, params, excluir, evalua)` | Entrena con los años anteriores a `evalua` y evalúa en ese año | pipeline, dict de métricas |
| `validar(modelo, objetivo, params, excluir)` | Validación temporal en tres pliegues (evalúa 2022, 2023 y 2024) | DataFrame de métricas por pliegue |
| `buscar(modelo, objetivo)` | Rejilla corta de `REJILLAS` evaluada con `validar` | DataFrame ordenado por PR-AUC medio, con columna `params` |
| `guardar(pipe, objetivo)` | Guarda el pipeline en `models/` | ruta del archivo |
| `predecir(registros, objetivo)` | Probabilidad de adición de uno o varios contratos | arreglo de probabilidades |
| `explicar(registro, fondo, objetivo, n)` | Los n factores que más mueven el riesgo (SHAP) | Serie variable → aporte |

1. `modelo`: `logistica`, `random_forest`, `lightgbm` o `catboost`.
2. `objetivo`: `y` (adición en tiempo o valor), `y_tiempo` o `y_valor`.
3. `params`: hiperparámetros del clasificador, por ejemplo `{"C": 0.01}` o `{"depth": 8, "learning_rate": 0.03}`.
4. `excluir`: variables que se quitan del modelo, por ejemplo `["fuente_principal"]`.
5. `evalua`: año evaluado; 2024 por defecto y 2025 para la prueba final.
6. Métricas: `pr_auc` (principal), `roc_auc`, `brier`, `precision_100`, `precision_10pct`, `recall_10pct`,
   `lift_10pct` y `tasa_base`.
7. Desde la terminal: `python src/modelo.py --modelo catboost --param depth=8 --validar` imprime las métricas por
   pliegue; `--evalua 2025` evalúa en prueba.

## 3. Experimentos en MLflow

1. Cada corrida registra como parámetros `modelo`, `objetivo`, los hiperparámetros y `excluir`, y como métricas la
   media de `validar` en los tres pliegues más la desviación del PR-AUC. El pipeline que devuelve `entrenar` se puede
   registrar como modelo de scikit-learn.
2. Experimentos sugeridos, en este orden:
   1. Modelos base: los cuatro modelos con `params=None` (4 corridas).
   2. Ajuste de hiperparámetros: cada fila de `buscar` es una corrida (22 corridas). Se puede ampliar `REJILLAS`.
   3. Selección de variables: el mejor modelo completo, sin las variables de importancia nula y sin
      `fuente_principal` (parámetro `excluir`).
   4. Objetivos: la configuración ganadora con `y_tiempo` e `y_valor`.
   5. Prueba: la configuración ganadora con `evalua=2025`, solo al final.
3. Regla de selección: mayor PR-AUC medio en los tres pliegues. Los modelos cuya diferencia con el mejor es menor que
   la desviación de su PR-AUC entre pliegues se consideran empatados, y entre ellos gana el de mayor `precision_100`
   medio (capacidad de revisión de un veedor). 2025 no se usa para elegir.
4. Selección de variables: se quita una variable si el PR-AUC medio baja menos de 0,005 sin ella. Con esta regla se
   excluye `fuente_principal` (aporte nulo y riesgo de fuga); la reducción a las variables de importancia nula no se
   adopta porque baja el PR-AUC.
5. Selección preliminar: CatBoost con `depth = 8`, `learning_rate = 0,03` y sin `fuente_principal` (`GANADOR` en
   `src/modelo.py`). Si las corridas de MLflow eligen otra configuración, se edita `GANADOR` y se corre
   `python src/modelo.py --ganador`.
6. Las semillas son fijas: las cifras de MLflow deben coincidir con las del notebook `02_modelos.ipynb`.

## 4. Uso en el tablero

1. Importación: agregar `src` al `sys.path` y `from modelo import predecir, explicar`; `from features import cargar`.
2. Probabilidad (elemento H): `predecir(registro, "y")`, y para las dos probabilidades del mockup v2,
   `predecir(registro, "y_tiempo")` y `predecir(registro, "y_valor")`.
3. Percentil de riesgo: comparar la probabilidad con las de los contratos de 2025,
   `ref = predecir(tabla[tabla["anio"] == 2025])` y `(ref < p).mean()`.
4. Factores (elemento I): `explicar(registro, fondo)`, con `fondo = tabla[tabla["anio"] < 2025].sample(300,
   random_state=42)`. Un aporte positivo sube el riesgo y uno negativo lo baja.
5. Precarga por ID (elemento G): la fila de `cargar()` con el `id_contrato` trae las 19 variables ya calculadas.
6. Vistas descriptivas (A a F): la misma tabla trae `anio`, `firma`, `departamento`, `modalidad`, `nombre_entidad`,
   `valor_inicial`, `dias_adic`, `y`, `y_tiempo` e `y_valor`.
7. Calibración: la probabilidad del modelo subestima la tasa de 2025 (ver sección 10 del notebook). Mientras se
   define la recalibración, la lectura principal es el percentil y el nivel de alerta; la probabilidad va como dato
   secundario.

### Campos de entrada

Todos son opcionales: los ausentes se tratan como faltantes. Las categóricas se envían como texto.
`fuente_principal` no la usa el modelo final y no se pide en el formulario.

| Variable | Tipo | Ejemplo | Origen en el formulario |
| --- | --- | --- | --- |
| `valor_inicial` | pesos | `500000000` | Valor inicial; el modelo usa su logaritmo |
| `plazo_inicial` | días | `120` | Plazo inicial |
| `respuestas` | número | `4` | Respuestas al proceso |
| `inicial_sobre_base` | razón | `0.95` | Valor adjudicado / precio base |
| `dias_publicacion_adjudicacion` | días | `30` | Fechas del proceso |
| `previos_entidad` | número | `25` | Contratos de obra previos de la entidad (desde la tabla) |
| `antiguedad_prov` | años | `3.5` | Antigüedad del proveedor en SECOP II |
| `proceso_compartido` | 0 o 1 | `0` | Proceso con varios contratos (lotes) |
| `proveedor_repetido` | 0 o 1 | `1` | El contratista ya contrató con la entidad |
| `nombre_entidad` | texto | `INVIAS` | Entidad contratante, escrita como en SECOP II |
| `modalidad` | texto | `Licitación pública` | Menor cuantía, Directa, Mínima cuantía, Licitación pública o Régimen especial |
| `departamento` | texto | `Antioquia` | Departamento de la entidad |
| `segmento_unspsc` | texto | `72` | Dos primeros dígitos del código UNSPSC |
| `destino_gasto` | texto | `Inversión` | Inversión o Funcionamiento |
| `condiciones_de_entrega` | texto | `A convenir` | Condiciones de entrega |
| `es_pyme` | texto | `Si` | Si o No |
| `tipodocproveedor` | texto | `NIT` | Tipo de documento del proveedor |
| `mes` | texto | `12` | Mes de la fecha de firma |
