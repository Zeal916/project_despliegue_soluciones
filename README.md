# Alerta de adiciones en contratos de obra pública (SECOP II)

Proyecto del curso Despliegue de Soluciones Analíticas (MIAD, Universidad de los Andes). Estima, al momento de la firma,
la probabilidad de que un contrato de obra pública registrado en SECOP II reciba adiciones en tiempo o en valor, para que
la DIARI de la Contraloría General de la República y las veedurías prioricen su seguimiento preventivo.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `src/ingest.py` | Descarga de las 6 fuentes de SECOP II para contratos de obra firmados entre 2019 y 2025 |
| `src/check_source.py` | Estado de las 6 tablas en datos.gov.co (filas y última actualización) |
| `src/features.py` | Tabla de modelado: un contrato por fila con las variables conocidas al firmar |
| `src/modelo.py` | Modelos, validación temporal, métricas, recalibración, `predecir` y `explicar` |
| `notebooks/01_eda_obra.ipynb` | Exploración de los datos |
| `notebooks/02_modelos.ipynb` | Comparación de cuatro modelos, selección, prueba en 2025 e interpretabilidad |
| `docs/modelos.md` | Guía de uso de los modelos para MLflow y el tablero |
| `docs/hallazgos_eda.md` | Hallazgos del EDA, revisiones del mockup e implicaciones para el modelado |
| `docs/evidencia/` | Registro de la indisponibilidad de Contratos Electrónicos en octubre de 2026 |
| `reports/figures/` | Figuras que genera el notebook |
| `data/raw/*.dvc` | Punteros DVC de los datos; los CSV están en DagsHub |
| `data/processed/`, `models/` | Tabla de modelado y modelos entrenados; se regeneran con `src/` (fuera de Git) |
| `docker/`, `docker-compose.yml` | Entorno con MLflow; la API y el tablero se agregan en las entregas 2 y 3 |
| `app/` | Reservada para la API y el tablero |

## Fuentes

Conjuntos abiertos de SECOP II en datos.gov.co:

1. Contratos Electrónicos (jbjy-vk9h)
2. Procesos de Contratación (p6dx-8zbt)
3. Ofertas por Proceso, en tres tablas por año de registro: bpan-xvj3 (hasta 2022), b28v-edj8 (2023-2024) y
   wi7w-2nvm (2025-2026)
4. Garantías (gjp9-cutm)
5. Proveedores Registrados (qmzu-gj57)
6. Adiciones (cb9c-h8sn)

## Reproducción

1. Clonar el repositorio:
   `git clone https://github.com/Zeal916/project_despliegue_soluciones.git`
2. Obtener los datos con `dvc pull` (requiere credenciales de DagsHub) o descargarlos de nuevo con
   `python src/ingest.py` (varios minutos; `--limit 200` para una prueba rápida).
3. Instalar el entorno del EDA (Python 3.11 o superior) con `pip install -r requirements-eda.txt` y ejecutar:
   `jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_obra.ipynb`
4. Generar la tabla de modelado con `python src/features.py`, guardar los modelos seleccionados con
   `python src/modelo.py --ganador` y ejecutar `notebooks/02_modelos.ipynb` con el Jupyter del mismo entorno.
5. Levantar MLflow con `docker compose up -d mlflow` y abrir http://localhost:5000.
