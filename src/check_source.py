"""Comprueba el estado de las tablas SECOP II usadas (conteo de filas y última modificación en origen).

Uso: python src/check_source.py   -> imprime una tabla con fecha/hora de la consulta (evidencia reproducible).
"""
import json, re, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE = "https://www.datos.gov.co"
TABLAS = {
    "jbjy-vk9h": "Contratos electrónicos",
    "p6dx-8zbt": "Procesos de contratación",
    "cb9c-h8sn": "Adiciones",
    "gjp9-cutm": "Garantías",
    "qmzu-gj57": "Proveedores registrados",
    "wi7w-2nvm": "Ofertas por proceso",
}


def get(url):
    return urllib.request.urlopen(url, timeout=90).read().decode("utf-8")


print(f"Consulta: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
print(f"{'id':10} {'tabla':28} {'filas':>12}  última modificación en origen (UTC)")
for tid, nombre in TABLAS.items():
    q = urllib.parse.urlencode({"$select": "count(*)"})
    filas = json.loads(get(f"{BASE}/resource/{tid}.json?{q}"))[0]["count"]
    meta = get(f"{BASE}/api/views/{tid}.json")
    ts = int(re.search(r'"rowsUpdatedAt"\s*:\s*(\d+)', meta).group(1))
    print(f"{tid:10} {nombre:28} {int(filas):>12,}  {datetime.fromtimestamp(ts, timezone.utc):%Y-%m-%d %H:%M}")
