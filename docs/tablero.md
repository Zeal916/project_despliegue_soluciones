# Tablero: alerta de adiciones en obra pública

Tablero en Streamlit que implementa el mockup v2 de la Entrega 1. Muestra dónde se concentran las adiciones en los
contratos de obra de SECOP II y estima, al momento de la firma, la probabilidad de que un contrato reciba adiciones en
tiempo o en valor.

En esta entrega el tablero carga los modelos directamente desde `models/` (`app/prediccion.py`). Cuando exista la
API, basta con definir la variable de entorno `API_URL` para que el tablero le pida las predicciones a ella, sin
cambiar las vistas.

## 1. Requisitos

- Python 3.11 o 3.12. Con Python 3.10 no instalan las versiones fijadas de numpy, pandas y scikit-learn.
- Git y acceso al repositorio.

## 2. Ejecución la primera vez

Desde PowerShell, en la carpeta donde se quiera guardar el proyecto:

```powershell
git clone https://github.com/Zeal916/project_despliegue_soluciones.git
cd project_despliegue_soluciones
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-eda.txt
pip install -r docker\requirements.txt
```

En Linux o macOS, el entorno se activa con `source .venv/bin/activate`, y en las rutas se usa `/` en lugar de `\`.

Luego se obtienen los datos y se entrenan los modelos:

```powershell
dvc pull                          # datos versionados en DagsHub
python src\features.py            # crea data\processed\obra_modelo.csv
python src\modelo.py --ganador    # crea models\modelo_y*.joblib
```

Si `dvc pull` no tiene acceso a DagsHub o reporta archivos faltantes, los datos se pueden descargar directamente de
datos.gov.co con `python src\ingest.py`, que tarda entre 10 y 30 minutos.

Por último, se abre el tablero:

```powershell
streamlit run app\dashboard.py
```

Se abre en http://localhost:8501. En la barra lateral debe aparecer «Predicciones con modelos locales (models/)».

## 3. Ejecuciones siguientes

No hay que reinstalar nada:

```powershell
cd project_despliegue_soluciones
.\.venv\Scripts\Activate.ps1
streamlit run app\dashboard.py
```

Si se actualizan los datos o cambian `src\features.py` o `src\modelo.py`, hay que volver a ejecutar
`python src\features.py` y `python src\modelo.py --ganador`.

## 4. Archivos

| Archivo | Contenido |
| --- | --- |
| `app/dashboard.py` | Punto de entrada: navegación, filtros globales y estado de los modelos |
| `app/comun.py` | Carga de datos, filtros, formato en español y estilo |
| `app/prediccion.py` | Probabilidad, percentil, nivel de alerta y factores SHAP con los modelos de `models/` |
| `app/vistas/panorama.py` | Vista 1, elementos A a F |
| `app/vistas/evaluar.py` | Vista 2, elementos G a K |
| `app/vistas/priorizados.py` | Vista 3, lista priorizada |
| `.streamlit/config.toml` | Tema del tablero |

## 5. Vistas

**Filtros globales** (barra lateral): año de firma, departamento, modalidad, entidad y tipo de adición (cualquiera,
en tiempo o en valor). Aplican a las vistas 1 y 3; el tipo de adición también elige el modelo cuyos factores muestra
la vista 2.

**Vista 1. Panorama de obras.**

| Elemento | Qué muestra |
| --- | --- |
| A | Contratos, tasa base, tasa en tiempo y en valor, extensión mediana del plazo y tasa por año de firma |
| B | Departamentos ordenados por tasa, con un número mínimo de contratos ajustable |
| C | Tasa por modalidad con su n; las modalidades con menos de 100 contratos se agrupan en «Otras» |
| D | Tasa por decil de valor inicial y mapa de calor de valor × plazo inicial |
| E | Firmas por mes y tasa de adición en tiempo y en valor |
| F | Entidades con un mínimo de contratos, ordenadas por tasa |

**Vista 2. Evaluar un contrato.**

| Elemento | Qué muestra |
| --- | --- |
| G | Formulario con las variables conocidas al firmar y precarga por ID de contrato. Excluye el estado, los días adicionados y la fecha de inicio, que delatan el desenlace |
| H | Riesgo total (máximo de los tres modelos), probabilidades en tiempo y en valor, percentil y semáforo |
| I | Factores SHAP que más suben o bajan el riesgo del contrato |
| J | Tasa de contratos similares (misma modalidad, decil de valor y departamento), de la entidad y de todas las obras, con su n |
| K | Lectura sugerida para el veedor |

**Vista 3. Contratos priorizados.** Lista del filtro ordenada por riesgo, con capacidad de revisión k, filtro de
alerta alta y descarga en CSV. Al seleccionar una fila se abre en la vista 2. Con «Mostrar desenlace registrado» se
calculan la precisión en k y el lift. Solo 2025 da una lectura honesta, porque 2019 a 2024 se usaron para entrenar.

## 6. Reglas del semáforo

Tomadas de `docs/modelos.md`, sección 3. El percentil compara la probabilidad del contrato con la de los contratos
firmados en 2025:

- **Alerta alta:** percentil 90 o más, es decir, el 10 % de mayor riesgo. Es el umbral evaluado en la prueba, con
  precisión de 0,725.
- **Media:** entre los percentiles 70 y 90. Solo como zona de atención; no fue evaluado.
- **Baja:** por debajo del percentil 70.

## 7. Problemas frecuentes

| Mensaje | Solución |
| --- | --- |
| `streamlit` no se reconoce | El entorno no está activo o le faltan librerías: actívelo e instale los requisitos |
| `Activate.ps1` no se reconoce | No existe `.venv` en la carpeta: créelo con `py -3.12 -m venv .venv` |
| PowerShell bloquea la activación | Ejecute una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| «No se encontró data/processed/obra_modelo.csv» | Ejecute `python src\features.py` |
| «Predicciones no disponibles» en la barra lateral | Faltan los modelos: ejecute `python src\modelo.py --ganador` |
| `dvc pull` reporta archivos faltantes | Los datos no están en DagsHub: use `python src\ingest.py` |
