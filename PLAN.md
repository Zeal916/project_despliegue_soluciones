# Plan de trabajo – SECOP II: riesgo de sobrecostos al firmar el contrato

Equipo: 3 personas. Actualizado: 2026-10-24.

## Fechas
| Entrega | Fecha | Estado |
|---|---|---|
| 1 | dom 25 oct 23:59 | en curso |
| 2 | dom 8 nov | |
| 3 | mar 24 nov (video incluido) | |

## Roles (Entrega 1)
| Parte | Responsable | Entrega 1 | Después |
|---|---|---|---|
| **1 – Definición del problema** | (compañero A) | Documento: contexto, pregunta de negocio, alcance, dónde y cómo conseguir los datos | Manual de usuario, video |
| **2 – Visualizaciones, modelo y mockup** | (compañero B) | Cómo se responde la pregunta con visualizaciones (descriptivo) y modelo (predictivo); mockup y su relación con la pregunta; **iterar el mockup con los hallazgos del EDA** | Tablero, API |
| **3 – EDA, DVC, Git y documentación** | (tú) | Repo Git, repo DVC, EDA y su documentación | Pipelines de datos, Docker, modelos/MLflow, despliegue |

Cada persona hace commits propios y escribe su sección (la nota es individual). El reporte de equipo de 1 página lo
redactan los tres con los aportes reales de cada uno.

**Dependencia clave:** la parte 2 necesita los hallazgos del EDA (parte 3) para iterar el mockup. Compartir pronto el
resumen de hallazgos (ver `docs/hallazgos_eda.md`, por crear).

## Decisión de infraestructura
- Desarrollo: **local con Docker Compose** (reproducible por los tres).
- Datos: **remoto DVC compartido** (Google Drive, S3 o DagsHub) para que nadie dependa del PC de otro.
- Despliegue final: **pendiente de confirmar con los tutores** si basta Docker local o se espera nube
  (Entrega 3 pide "soportes de los recursos empleados para el despliegue"). Plan B: VM pequeña en nube con el mismo compose.

## Fase 0 – Bases (parte 3, hoy)
- [x] Instalar Docker Desktop, DVC, MLflow (venv del proyecto)
- [x] Estructura del repo: `data/ notebooks/ src/ app/ docker/ reports/`
- [x] `git init`, `.gitignore`, `README`, remoto en GitHub, invitar a los compañeros (README pendiente)
- [ ] `dvc init` + remoto DVC compartido
- [x] `src/ingest.py`: descarga vía Socrata (contratos, adiciones, garantías, proveedores), sector Salud, 2017→hoy
- [ ] Dataset base versionado con DVC (`dvc add`), commit y push
- [x] Dockerfile base de Python + `docker-compose.yml` vacío (api, dashboard, mlflow)

## Fase 1 – Entrega 1 (hoy → dom 25)
- [ ] Parte 3: EDA (tasa de adiciones por año/modalidad/tipo/departamento, nulos, tamaño vs adiciones, fuga en `valor_del_contrato`, `saldo_cdp`, `dias_adicionados`)
- [ ] Parte 2: maqueta (panorama de riesgo, lista priorizada, simulador vía API)
- [ ] Partes 1–3 + todos: reporte ≤10 pág. en el orden de la rúbrica; reporte de equipo 1 pág.
- [ ] Capturas/enlaces de repos Git y DVC como soporte

## Fase 2 – Entrega 2 (sem 4–5)
Pipeline de features, split temporal, baselines (logística, RF, LightGBM/XGBoost), MLflow, tablero con datos reales.

## Fase 3 – Entrega 3 (sem 6–8)
Empaquetado del modelo, API FastAPI (`/predict`, `/health`), contenedores, despliegue, manuales, video ≤10 min.
