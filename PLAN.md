# Plan de trabajo. SECOP II: riesgo de sobrecostos al firmar el contrato

Equipo: 3 personas. Actualizado: 2026-11-07.

## Fechas
| Entrega | Fecha | Estado |
|---|---|---|
| 1 | dom 25 oct 23:59 | entregada |
| 2 | dom 8 nov | en curso |
| 3 | mar 24 nov (video incluido) | |

## Roles (Entrega 1)
| Parte | Responsable | Entrega 1 | Después |
|---|---|---|---|
| **1. Definición del problema** | (compañero A) | Documento: contexto, pregunta de negocio, alcance, dónde y cómo conseguir los datos | Manual de usuario, video |
| **2. Visualizaciones, modelo y mockup** | (compañero B) | Cómo se responde la pregunta con visualizaciones (descriptivo) y modelo (predictivo); mockup y su relación con la pregunta; **iterar el mockup con los hallazgos del EDA** | Tablero, API |
| **3. EDA, DVC, Git y documentación** | (tú) | Repo Git, repo DVC, EDA y su documentación | Pipelines de datos, Docker, modelos/MLflow, despliegue |

Cada persona hace commits propios y escribe su sección (la nota es individual). El reporte de equipo de 1 página lo
redactan los tres con los aportes reales de cada uno.

**Dependencia clave:** la parte 2 necesita los hallazgos del EDA (parte 3) para iterar el mockup. Compartir pronto el
resumen de hallazgos (ver `docs/hallazgos_eda.md`).

## Decisión de infraestructura
- Desarrollo: **local con Docker Compose** (reproducible por los tres).
- Datos: **remoto DVC compartido** (Google Drive, S3 o DagsHub) para que nadie dependa del PC de otro.
- Despliegue final: **pendiente de confirmar con los tutores** si basta Docker local o se espera nube
  (Entrega 3 pide "soportes de los recursos empleados para el despliegue"). Plan B: VM pequeña en nube con el mismo compose.

## Fase 0: bases (parte 3, hoy)
- [x] Instalar Docker Desktop, DVC, MLflow (venv del proyecto)
- [x] Estructura del repo: `data/ notebooks/ src/ app/ docker/ reports/`
- [x] `git init`, `.gitignore`, `README`, remoto en GitHub, invitar a los compañeros
- [x] `dvc init` + remoto DVC compartido (DagsHub)
- [x] `src/ingest.py`: descarga vía Socrata de las 6 fuentes SECOP II del alcance, contratos de obra 2019-2025
- [x] Dataset base versionado con DVC (`dvc add`), commit y push
- [x] Dockerfile base de Python + `docker-compose.yml` vacío (api, dashboard, mlflow)

## Fase 1: Entrega 1 (hoy → dom 25)
- [x] Parte 3: EDA (`notebooks/01_eda_obra.ipynb`, hallazgos en `docs/hallazgos_eda.md`)
- [x] Parte 2: maqueta (panorama de riesgo, lista priorizada, simulador vía API)
- [x] Partes 1 a 3 y todos: reporte ≤10 pág. en el orden de la rúbrica; reporte de equipo 1 pág.
- [x] Capturas/enlaces de repos Git y DVC como soporte

## Fase 2: Entrega 2 (semanas 4 y 5)
- [x] Tabla de modelado (`src/features.py`) y modelos (`src/modelo.py`): logística, Random Forest, LightGBM y CatBoost
- [x] Validación temporal 2022-2024, búsqueda corta, selección de variables y prueba en 2025 (`notebooks/02_modelos.ipynb`)
- [x] Recalibración, explicaciones SHAP y guía para MLflow y el tablero (`docs/modelos.md`)
- [x] Experimentos registrados en MLflow (EC2) y confirmación de la selección (`src/experimentos.py`, `docs/mlflow_ec2.md`)
- [ ] Tablero con datos reales y predicciones del modelo
- [ ] Reporte de 10 páginas y reporte de trabajo en equipo

## Fase 3: Entrega 3 (semanas 6 a 8)
Empaquetado del modelo, API FastAPI (`/predict`, `/health`), contenedores, despliegue, manuales, video ≤10 min.
