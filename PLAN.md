# Plan de trabajo – SECOP II: riesgo de sobrecostos al firmar el contrato

Equipo: 3 personas. Actualizado: 2026-10-24.

## Fechas
| Entrega | Fecha | Estado |
|---|---|---|
| 1 | dom 25 oct 23:59 | en curso |
| 2 | dom 8 nov | |
| 3 | mar 24 nov (video incluido) | |

## Roles propuestos (a confirmar entre los tres)
| Rol | Responsable | Entrega 1 | Después |
|---|---|---|---|
| **P1 – Plataforma y datos** | (tú) | Repo Git, DVC, ingesta, dataset base, esqueleto Docker | API, Docker/compose, despliegue, MLflow server |
| **P2 – Análisis y modelos** | | EDA + chequeo de fuga + definición del target | Modelos, experimentos MLflow, SHAP |
| **P3 – Producto y reporte** | | Maqueta, problema/contexto, pregunta de negocio, ensamblaje del reporte | Tablero, manuales, video |

Cada persona escribe su propia sección del reporte y hace commits propios (la nota es individual).

## Decisión de infraestructura
- Desarrollo: **local con Docker Compose** (reproducible por los tres).
- Datos: **remoto DVC compartido** (Google Drive, S3 o DagsHub) para que nadie dependa del PC de otro.
- Despliegue final: **pendiente de confirmar con los tutores** si basta Docker local o se espera nube
  (Entrega 3 pide "soportes de los recursos empleados para el despliegue"). Plan B: VM pequeña en nube con el mismo compose.

## Fase 0 – Bases (P1, hoy)
- [ ] Instalar Docker Desktop, DVC, MLflow (venv del proyecto)
- [ ] Estructura del repo: `data/ notebooks/ src/ app/ docker/ reports/`
- [ ] `git init`, `.gitignore`, `README`, remoto en GitHub, invitar a P2 y P3
- [ ] `dvc init` + remoto DVC compartido
- [ ] `src/ingest.py`: descarga vía Socrata (contratos, adiciones, garantías, proveedores), sector Salud, 2017→hoy
- [ ] Dataset base versionado con DVC (`dvc add`), commit y push
- [ ] Dockerfile base de Python + `docker-compose.yml` vacío (api, dashboard, mlflow)

## Fase 1 – Entrega 1 (hoy → dom 25)
- [ ] P2: EDA (tasa de adiciones por año/modalidad/tipo/departamento, nulos, tamaño vs adiciones, fuga en `valor_del_contrato`, `saldo_cdp`, `dias_adicionados`)
- [ ] P3: maqueta (panorama de riesgo, lista priorizada, simulador vía API)
- [ ] P3 + todos: reporte ≤10 pág. en el orden de la rúbrica; reporte de equipo 1 pág.
- [ ] Capturas/enlaces de repos Git y DVC como soporte

## Fase 2 – Entrega 2 (sem 4–5)
Pipeline de features, split temporal, baselines (logística, RF, LightGBM/XGBoost), MLflow, tablero con datos reales.

## Fase 3 – Entrega 3 (sem 6–8)
Empaquetado del modelo, API FastAPI (`/predict`, `/health`), contenedores, despliegue, manuales, video ≤10 min.
