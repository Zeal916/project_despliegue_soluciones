#!/bin/bash
# Instala MLflow en una instancia EC2 Ubuntu 24.04 como servicio systemd.
# Se puede pegar como "User data" al lanzar la instancia o correr con:
#   curl -fsSL https://raw.githubusercontent.com/Zeal916/project_despliegue_soluciones/main/docker/ec2_mlflow.sh | sudo bash
# El servicio arranca solo al encender la instancia, también después de detenerla.
set -euo pipefail
USUARIO=ubuntu
DIR=/home/$USUARIO/mlflow

apt-get update -y
apt-get install -y python3-venv
sudo -u $USUARIO python3 -m venv $DIR/venv
sudo -u $USUARIO $DIR/venv/bin/pip install -q "mlflow==3.5.1" "sqlalchemy<2.1"

# --artifacts-destination: el servidor recibe los modelos por HTTP (el cliente no escribe en su disco).
# --allowed-hosts "*": MLflow 3.5 rechaza por defecto peticiones a la IP pública.
cat > /etc/systemd/system/mlflow.service <<EOF
[Unit]
Description=MLflow tracking server
After=network.target

[Service]
User=$USUARIO
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/mlflow server --host 0.0.0.0 --port 5000 \
  --backend-store-uri sqlite:///$DIR/mlflow.db --artifacts-destination $DIR/artifacts \
  --allowed-hosts "*"
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now mlflow
