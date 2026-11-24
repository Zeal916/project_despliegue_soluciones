# Despliegue de la API y el tablero en AWS EC2

La API (FastAPI, puerto 8000) y el tablero (Streamlit, puerto 8501) corren como contenedores Docker en la misma
instancia EC2 del servidor MLflow (`docs/mlflow_ec2.md`). El tablero le pide las predicciones a la API por la red interna
de Docker Compose (`http://api:8000`).

```
Usuario ──▶ :8501 tablero (Streamlit) ──▶ api:8000 API (FastAPI + secop_obra_modelo)
Usuario ──▶ :8000/docs API
Equipo  ──▶ :5000 MLflow (servicio systemd)
```

## 1. Preparar la instancia

La instancia de MLflow se lanzó con 8 GB de disco. Las imágenes ocupan unos 4 GB y los modelos se cargan en memoria,
así que se amplía una vez, con la instancia detenida:

1. EC2 > Instances > la instancia > Instance state > **Stop**.
2. Actions > Instance settings > **Change instance type**: `t3.medium` (2 vCPU, 4 GB de RAM).
3. Pestaña Storage > el volumen > Actions > **Modify volume**: 30 GB. Al encender, Ubuntu amplía la partición.
4. Pestaña Security > el grupo de seguridad > **Edit inbound rules**: agregar TCP 8000 y TCP 8501 con origen
   `0.0.0.0/0` (para que los tutores puedan abrirlos). SSH (22) y MLflow (5000) quedan con origen "My IP".
5. Instance state > **Start** y copiar la nueva IP pública.

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
2. Grupo de seguridad con los puertos 22, 5000, 8000 y 8501.
3. Terminal SSH con `whoami`, `curl -s ifconfig.me`, `docker compose ps` y `docker images`.
4. `http://<IP>:8000/docs` con una petición a `/predict` ejecutada y su respuesta.
5. El tablero con la IP en la barra de direcciones: la vista de evaluación de un contrato y la lista priorizada.

## 5. Detener

Instance state > **Stop**, sin terminar. Al encenderla de nuevo, Docker y MLflow arrancan solos y los contenedores se
levantan otra vez (`restart: unless-stopped`); solo cambia la IP pública.
