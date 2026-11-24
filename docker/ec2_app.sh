#!/bin/bash
# Despliega la API (puerto 8000) y el tablero (puerto 8501) en una instancia
# EC2 Ubuntu 24.04 con Docker Compose (docs/despliegue_ec2.md).
# Se corre por SSH, también para actualizar después de un push:
#   curl -fsSL https://raw.githubusercontent.com/Zeal916/project_despliegue_soluciones/main/docker/ec2_app.sh | sudo bash
# Los contenedores vuelven a arrancar solos al encender la instancia.
set -euo pipefail
USUARIO=ubuntu
REPO=https://github.com/Zeal916/project_despliegue_soluciones.git
DIR=/home/$USUARIO/app

# Las dos imágenes ocupan unos 4 GB más la caché de construcción.
LIBRE=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
if [ "$LIBRE" -lt 10 ]; then
  echo "Solo hay ${LIBRE} GB libres en /. Amplíe el volumen a 30 GB (docs/despliegue_ec2.md)." >&2
  exit 1
fi

apt-get update -y
apt-get install -y docker.io docker-compose-v2 git
systemctl enable --now docker
usermod -aG docker $USUARIO

# 2 GB de swap: margen de memoria para construir las imágenes
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if [ -d $DIR/.git ]; then
  sudo -u $USUARIO git -C $DIR pull --ff-only
else
  sudo -u $USUARIO git clone $REPO $DIR
fi

cd $DIR
docker compose up -d --build api dashboard
docker builder prune -f
docker compose ps
