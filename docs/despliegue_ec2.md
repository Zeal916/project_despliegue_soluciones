# Despliegue de la API y el tablero en AWS EC2

La API (FastAPI, puerto 8000) y el tablero (Streamlit, puerto 8501) corren como contenedores Docker en una instancia
EC2 propia, separada del servidor MLflow (`docs/mlflow_ec2.md`). El tablero le pide las predicciones a la API por la red
interna de Docker Compose (`http://api:8000`).

```
Usuario ──▶ :8501 tablero (Streamlit) ──▶ api:8000 API (FastAPI + secop_obra_modelo)
Usuario ──▶ :8000/docs API
```

## 1. Lanzar la instancia

EC2 > Launch instance:

| Campo | Valor |
| --- | --- |
| Name | `secop-app` |
| AMI | Ubuntu Server 26.04 LTS (64-bit x86) |
| Instance type | `t3.medium` (2 vCPU, 4 GB de RAM; las imágenes cargan los modelos en memoria) |
| Key pair | `vockey` (`labsuser.pem` en AWS Academy) |
| Storage | 30 GB gp3 (las dos imágenes ocupan unos 4 GB más la caché de construcción) |
| Security group | SSH 22 desde "My IP"; TCP 8000 y TCP 8501 desde `0.0.0.0/0` |

Opcional: en Advanced details > User data, pegar lo siguiente para que el paso 2 corra solo al arrancar:

```bash
#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Zeal916/project_despliegue_soluciones/main/docker/ec2_app.sh | bash
```

## 2. Desplegar

Desde la carpeta donde está `labsuser.pem`:

```bash
ssh -i labsuser.pem ubuntu@<IP pública>
curl -fsSL https://raw.githubusercontent.com/Zeal916/project_despliegue_soluciones/main/docker/ec2_app.sh | sudo bash
```

El script (`docker/ec2_app.sh`) instala Docker, agrega 2 GB de swap, clona el repositorio en `~/app` y construye y
levanta los servicios `api` y `dashboard` del `docker-compose.yml`. La primera vez tarda de 5 a 10 minutos. Para
publicar cambios después de un push, se vuelve a correr el mismo comando.

## 3. Comprobar

| Qué | Dónde |
| --- | --- |
| Estado de la API | `http://<IP>:8000/health` → `{"estado":"ok",...}` |
| Documentación de la API (probar `/predict`) | `http://<IP>:8000/docs` |
| Tablero | `http://<IP>:8501`; la barra lateral dice "Predicciones con API en http://api:8000" |
| Contenedores | `cd ~/app && docker compose ps` (api `healthy`, dashboard `Up`) |
| Registros | `docker compose logs -f api` |

## 4. Capturas para la entrega

1. Consola de EC2: instancia en ejecución con ID, tipo, IP pública y usuario de AWS (esquina superior derecha).
2. Grupo de seguridad con los puertos 22, 8000 y 8501.
3. Terminal SSH con `whoami`, `curl -s ifconfig.me`, `docker compose ps` y `docker images`.
4. `http://<IP>:8000/docs` con una petición a `/predict` ejecutada y su respuesta.
5. El tablero con la IP en la barra de direcciones: la vista de evaluación de un contrato y la lista priorizada.

Las capturas del despliegue del 24 de noviembre de 2026 (instancia `i-090d439ffe30584e6`, IP 54.210.63.63) están en
`docs/evidencia/despliegue/`:

| Archivo | Qué muestra |
| --- | --- |
| `01_instancia_ec2.png` | Instancia `secop-app` en ejecución, tipo `t3.medium`, IP pública y usuario de AWS |
| `02_almacenamiento.png` | Volumen raíz de 30 GiB |
| `03_grupo_seguridad.png` | Reglas de entrada: 22 desde la IP del equipo, 8000 y 8501 abiertos |
| `04_terminal_ssh_docker.png` | `whoami`, IP pública, `docker compose ps`, `docker images` y `/health` |
| `05_api_docs.png` | Documentación de la API con sus tres rutas |
| `06_api_predict.png` | Petición a `POST /predict` y respuesta 200 |
| `07_tablero_panorama.png` | Panorama del tablero; la barra lateral indica que predice con la API |
| `08_tablero_evaluar.png` | Evaluación de un contrato con probabilidad, alerta y factores SHAP |
| `09_tablero_priorizados.png` | Contratos de 2025 priorizados con las predicciones de la API |

## 5. Detener

Instance state > **Stop**, sin terminar. Al encenderla de nuevo, Docker arranca solo y los contenedores se
levantan otra vez (`restart: unless-stopped`); solo cambia la IP pública.
