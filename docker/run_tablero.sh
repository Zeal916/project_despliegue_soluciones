#!/bin/bash
# Arranca el tablero en el puerto de la variable PORT (8501 por defecto).
# Si se define API_URL (por ejemplo http://IP_DE_LA_API:8000), las predicciones
# se piden a la API; si no, se calculan con el paquete secop_obra_modelo.
# --client.toolbarMode viewer oculta los menús de desarrollo (botón Deploy).
streamlit run app/dashboard.py --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 --client.toolbarMode viewer
