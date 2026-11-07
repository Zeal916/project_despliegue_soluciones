# Modelos: guía para MLflow y el tablero

Guía para los integrantes que registran los experimentos en MLflow y construyen el tablero. Explica cómo preparar el
entorno, qué registrar en MLflow y cómo obtener predicciones y explicaciones desde el tablero. Las cifras y figuras
están en `notebooks/02_modelos.ipynb`.

## 1. Preparar el entorno

1. Instalar las dependencias en un entorno de Python 3.11 o 3.12:

   ```bash
   pip install -r requirements-eda.txt
   ```

2. Descargar los datos crudos desde DagsHub (pide las credenciales de DagsHub):

   ```bash
   dvc pull
   ```

3. Generar la tabla de modelado, que escribe `data/processed/obra_modelo.csv` con 40.170 contratos:

   ```bash
   python src/features.py
   ```

4. Entrenar y guardar los modelos seleccionados, que escribe `models/modelo_y.joblib`,
   `models/modelo_y_tiempo.joblib` y `models/modelo_y_valor.joblib`:

   ```bash
   python src/modelo.py --ganador
   ```

5. Opcional, para reproducir las cifras del notebook (unos 10 minutos):

   ```bash
   cd notebooks
   python -m jupyter nbconvert --to notebook --execute --inplace 02_modelos.ipynb
   ```

La tabla y los modelos quedan fuera de Git; cada integrante los genera con los pasos 3 y 4.

## 2. Registrar experimentos en MLflow

### 2.1. Qué registrar en cada corrida

| Elemento | Qué se registra | Cómo se obtiene |
| --- | --- | --- |
| Parámetros | `modelo`, `objetivo`, hiperparámetros y variables excluidas | Los argumentos de la llamada |
| Métricas de validación | Media de cada métrica en 2022, 2023 y 2024, y desviación del PR-AUC | `validar(...)`, con `.mean()` y `["pr_auc"].std()` |
| Métricas de prueba | Métricas en 2025, solo en el experimento 5 | Segundo valor que devuelve `entrenar(..., evalua=2025)` |
| Modelo | Pipeline de scikit-learn entrenado con 2019 a 2024 | Primer valor que devuelve `entrenar(..., evalua=2025)` |

Ejemplo de una corrida de validación:

```python
import sys
sys.path.insert(0, "src")

from modelo import validar

metricas = validar("catboost", params={"depth": 6, "learning_rate": 0.03})
media = metricas.mean()               # una métrica por columna
desviacion = metricas["pr_auc"].std()
```

### 2.2. Experimentos

Todas las corridas usan las funciones de `src/modelo.py`. Total: 35 corridas.

| # | Experimento | Llamadas | Corridas |
| --- | --- | --- | --- |
| 1 | Modelos base | `validar(m)` para cada `m` en `MODELOS` | 4 |
| 2 | Ajuste de hiperparámetros | Cada fila de `buscar(m)`; la columna `params` trae los hiperparámetros | 22 |
| 3 | Selección de variables | `validar` con la configuración ganadora y `excluir` igual a: nada; las 3 variables sin aporte; `["fuente_principal"]`; `GANADOR["excluir"]` | 4 |
| 4 | Objetivos | `validar` con la configuración final y `objetivo` igual a `"y_tiempo"` y `"y_valor"` | 2 |
| 5 | Prueba | `entrenar(..., evalua=2025)` con la configuración final para `"y"`, `"y_tiempo"` y `"y_valor"` | 3 |

Las 3 variables sin aporte son `proveedor_repetido`, `tipodocproveedor` y `proceso_compartido`.

### 2.3. Aplicar la regla de selección

1. Ordenar las corridas de los experimentos 1 y 2 por PR-AUC medio de validación.
2. La de mayor valor es la seleccionada; no hay criterio de desempate y 2025 no interviene.
3. Comparar con `GANADOR` en `src/modelo.py`. Si coincide, la selección queda confirmada.
4. Si no coincide, editar `GANADOR` con la nueva configuración y correr `python src/modelo.py --ganador`.

Las semillas son fijas: las cifras de MLflow deben coincidir con las del notebook.

## 3. Usar el modelo en el tablero

Los elementos G, H e I corresponden a la vista "Evaluar un contrato" del mockup v2 (Entrega 1, figura 4).

```python
import sys
sys.path.insert(0, "src")

from features import cargar
from modelo import explicar, predecir

tabla = cargar()
contrato = {"valor_inicial": 500_000_000, "nombre_entidad": "INVIAS",
            "modalidad": "Licitación pública", "plazo_inicial": 180, "mes": 12}

# Elemento H: probabilidades recalibradas
p = {o: predecir(contrato, o)[0] for o in ["y", "y_tiempo", "y_valor"]}
riesgo_total = max(p.values())

# Percentil frente a los contratos de 2025 y alerta en el 10 % de mayor riesgo
referencia = predecir(tabla[tabla["anio"] == 2025])
percentil = (referencia < p["y"]).mean()
alerta = percentil >= 0.9

# Elemento I: los cinco factores que más mueven el riesgo
fondo = tabla[tabla["anio"] < 2025].sample(300, random_state=42)
factores = explicar(contrato, fondo)

# Elemento G: precargar un contrato existente por su ID
fila = tabla[tabla["id_contrato"] == "CO1.PCCNTR.8645608"]
p_fila = predecir(fila)
```

1. Las tres probabilidades salen de modelos independientes. El riesgo total que se muestra es el máximo de las tres,
   para que no quede por debajo del riesgo de uno de sus componentes.
2. El percentil y la alerta son la lectura principal: la probabilidad subestima la tasa de 2025 aun después de la
   recalibración (sección 5).
3. La alerta en el 10 % de mayor riesgo es el umbral evaluado en el notebook (precisión de 0,725 en 2025).
4. En `factores`, un aporte positivo sube el riesgo y uno negativo lo baja. `explicar` tarda menos de medio segundo
   por contrato.
5. Las vistas A a F usan la misma tabla: `anio`, `firma`, `departamento`, `modalidad`, `nombre_entidad`,
   `valor_inicial`, `dias_adic`, `y`, `y_tiempo` e `y_valor`. `estado_contrato` es posterior a la firma y no va en el
   formulario.

## 4. Referencia

### 4.1. Funciones

`src/modelo.py`:

| Función | Qué hace | Devuelve |
| --- | --- | --- |
| `entrenar(modelo, objetivo, params, excluir, evalua, datos)` | Entrena con los años anteriores a `evalua` y evalúa en ese año | Pipeline y diccionario de métricas |
| `validar(modelo, objetivo, params, excluir, datos)` | Llama a `entrenar` con `evalua` igual a 2022, 2023 y 2024 | DataFrame con una fila por año |
| `buscar(modelo, objetivo, excluir, datos)` | Corre `validar` para cada combinación de `REJILLAS[modelo]` | DataFrame ordenado por PR-AUC medio |
| `calibrar(modelo, objetivo, params, excluir, datos)` | Ajusta la recalibración de Platt con las predicciones de 2024 de un modelo entrenado con 2019 a 2023 | Coeficientes `(a, b)` |
| `guardar(pipe, objetivo, platt)` | Guarda el pipeline y los coeficientes en `models/modelo_{objetivo}.joblib` | Ruta del archivo |
| `predecir(registros, objetivo, calibrada)` | Probabilidad de adición de un contrato (dict) o varios (DataFrame) | Arreglo de probabilidades |
| `explicar(registro, fondo, objetivo, n)` | Valores SHAP del contrato agrupados por variable | Serie con los `n` mayores aportes |

`src/features.py`:

| Función | Qué hace | Devuelve |
| --- | --- | --- |
| `construir()` | Cruza las fuentes de `data/raw/` y calcula objetivos y variables | DataFrame de 40.170 contratos |
| `cargar()` | Lee `data/processed/obra_modelo.csv` con las categóricas como texto | DataFrame |

Parámetros:

| Parámetro | Valores | Por defecto |
| --- | --- | --- |
| `modelo` | `"logistica"`, `"random_forest"`, `"lightgbm"`, `"catboost"` | |
| `objetivo` | `"y"` (adición en tiempo o en valor), `"y_tiempo"`, `"y_valor"` | `"y"` |
| `params` | Diccionario de hiperparámetros, por ejemplo `{"depth": 6, "learning_rate": 0.03}` | Valores base |
| `excluir` | Lista de variables que no entran al modelo | Ninguna |
| `evalua` | Año evaluado; 2025 es la prueba | 2024 |
| `datos` | Tabla de modelado | Se lee con `cargar()` |
| `calibrada` | Aplica la recalibración guardada | `True` |
| `fondo` | Muestra de 100 a 500 contratos de referencia para SHAP | |
| `n` | Número de factores | 5 |

Línea de comandos:

| Comando | Qué hace |
| --- | --- |
| `python src/modelo.py --modelo catboost --param depth=6 --validar` | Métricas por año de validación |
| `python src/modelo.py --modelo catboost --evalua 2025` | Métricas de prueba |
| `python src/modelo.py --excluir fuente_principal --validar` | Validación sin una variable |
| `python src/modelo.py --ganador` | Entrena, recalibra y guarda la configuración `GANADOR` para los tres objetivos |

### 4.2. Campos de entrada

Todos son opcionales: los ausentes se tratan como faltantes. Las categóricas se envían como texto. El modelo final no
usa `fuente_principal`, `proveedor_repetido`, `tipodocproveedor` ni `proceso_compartido`.

| Variable | Tipo | Ejemplo | Descripción |
| --- | --- | --- | --- |
| `valor_inicial` | pesos | `500000000` | Valor inicial; el modelo usa su logaritmo |
| `plazo_inicial` | días | `120` | Plazo inicial |
| `respuestas` | número | `4` | Respuestas al proceso |
| `inicial_sobre_base` | razón | `0.95` | Valor adjudicado / precio base |
| `dias_publicacion_adjudicacion` | días | `30` | Días entre la publicación y la adjudicación del proceso |
| `nombre_entidad` | texto | `INVIAS` | Entidad, escrita como en SECOP II; `predecir` calcula con ella `tasa_entidad` |
| `tasa_entidad` | razón | `0.47` | Tasa histórica de adición de la entidad; no se envía si llega `nombre_entidad` |
| `previos_entidad` | número | `25` | Contratos de obra previos de la entidad |
| `antiguedad_prov` | años | `3.5` | Antigüedad del proveedor en SECOP II |
| `modalidad` | texto | `Licitación pública` | Menor cuantía, Directa, Mínima cuantía, Licitación pública o Régimen especial |
| `departamento` | texto | `Antioquia` | Departamento de la entidad |
| `segmento_unspsc` | texto | `72` | Dos primeros dígitos del código UNSPSC |
| `destino_gasto` | texto | `Inversión` | Inversión o Funcionamiento |
| `condiciones_de_entrega` | texto | `A convenir` | Condiciones de entrega |
| `es_pyme` | texto | `Si` | Si o No |
| `mes` | texto | `12` | Mes de la fecha de firma |

### 4.3. Métricas

| Métrica | Qué mide |
| --- | --- |
| `pr_auc` | Área bajo la curva de precisión y exhaustividad; métrica principal |
| `roc_auc` | Área bajo la curva ROC; no depende de la tasa base |
| `brier` | Error cuadrático de la probabilidad; menor es mejor |
| `precision_100` | Proporción con adición entre los 100 contratos de mayor riesgo |
| `precision_10pct` | Proporción con adición en el 10 % de mayor riesgo |
| `recall_10pct` | Proporción de los contratos con adición que quedan en el 10 % de mayor riesgo |
| `lift_10pct` | `precision_10pct` dividida por la tasa base |
| `tasa_base` | Proporción de contratos con adición en el año evaluado |

## 5. Decisiones del modelo

1. **Partición temporal.** Cada modelo se entrena con los años anteriores al evaluado. La selección usa 2022, 2023 y
   2024; 2025 se reserva como prueba, porque la práctica de registro de las adiciones cambia entre años.
2. **Regla de selección.** Gana la configuración de mayor PR-AUC medio en validación. Los cuatro modelos quedan
   cerca (0,514 a 0,528), por lo que la confirmación en MLflow es parte del proceso.
3. **Entidad.** El nombre de la entidad se reemplaza por su tasa histórica de adición, calculada solo con años
   anteriores al de la firma. Así ningún contrato de entrenamiento se codifica con desenlaces posteriores de su
   entidad.
4. **Variables.** De 19 candidatas se quita toda variable cuya salida baja el PR-AUC medio menos de 0,005. Con esa
   regla salen las 3 variables sin aporte. `fuente_principal` también sale, por riesgo de fuga: sus montos se
   actualizan con las adiciones. Quedan 15 variables.
5. **Recalibración.** El modelo subestima la probabilidad porque la tasa subió de 35 % en 2024 a 47 % en 2025. La
   recalibración de Platt, ajustada con 2024, reduce el error (Brier de 0,253 a 0,232) sin cambiar el orden de los
   contratos, pero no alcanza la tasa de 2025.
6. **Configuración actual.** CatBoost con `depth=6` y `learning_rate=0.03`, definida en `GANADOR` de
   `src/modelo.py`.

Las cifras de esta sección están en las secciones 6, 7 y 10 del notebook.
