# Experimentos en MLflow sobre AWS EC2

Los experimentos de `docs/modelos.md` (sección 2.2) se registran con `src/experimentos.py` en un servidor MLflow que
corre en EC2. El script corre en el equipo de un integrante y envía parámetros, métricas y modelos al servidor.

## 1. Lanzar la instancia

1. EC2 > Launch instance: Ubuntu Server 24.04, tipo `t2.micro` o `t3.small`, 8 GB de disco, un par de llaves.
2. Grupo de seguridad: SSH (22) y TCP 5000 con origen "My IP".
3. En Advanced details > User data, pegar el contenido de `docker/ec2_mlflow.sh`. Si la instancia ya existe, conectarse
   por SSH y correr `sudo bash ec2_mlflow.sh`.
4. A los 2 o 3 minutos, abrir `http://<IP pública>:5000`. Comprobar con `systemctl status mlflow` si no responde.

## 2. Registrar los experimentos

Con el entorno de `docs/modelos.md` (sección 1) y la tabla `data/processed/obra_modelo.csv`:

```bash
pip install "mlflow==3.5.1" "sqlalchemy<2.1"
MLFLOW_TRACKING_URI=http://<IP pública>:5000 python src/experimentos.py      # bash
$env:MLFLOW_TRACKING_URI="http://<IP pública>:5000"; python src/experimentos.py   # PowerShell
```

Tarda de 2 a 5 minutos y crea 5 experimentos (`secop_obra/1_modelos_base` a `secop_obra/5_prueba_2025`) con 35 corridas,
y tres modelos registrados (`riesgo_adicion_y`, `riesgo_adicion_y_tiempo`, `riesgo_adicion_y_valor`). Al final imprime si
la configuración ganadora coincide con `GANADOR` de `src/modelo.py`. `--solo 1 2` corre solo algunos experimentos.

## 3. Capturas para la entrega

La entrega pide que se vean el usuario y la IP de la máquina en EC2 y la IP en MLflow:

1. Consola de EC2 con la instancia en ejecución: ID, IP pública y usuario de AWS (esquina superior derecha).
2. Terminal SSH con `whoami`, `curl -s ifconfig.me` y `systemctl status mlflow`.
3. MLflow con la IP en la barra de direcciones: lista de experimentos.
4. Experimento 2 en vista de tabla, ordenado por `val_pr_auc`, y la gráfica de comparación de corridas.
5. Una corrida del experimento 5: parámetros, métricas de prueba y el modelo (en MLflow 3 aparece en "Logged models").
6. Models: los tres modelos registrados.

Al terminar, detener la instancia (Instance state > Stop), sin terminarla. La IP pública cambia al encenderla de nuevo;
el servicio MLflow arranca solo.
