"""Descarga SECOP II (Socrata, datos.gov.co): contratos de Salud desde 2017 y sus adiciones en valor.

Uso: python src/ingest.py [--limit N]   (N solo para pruebas)
Solo stdlib. Opcional: SOCRATA_APP_TOKEN en el entorno para evitar throttling.
Excluye PII (nombres, documentos, cuentas) y variables de ejecución (fuga de información).
"""
import argparse, csv, json, os, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://www.datos.gov.co/resource"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
PAGE = 50_000

CONTRATOS = "jbjy-vk9h"
CONTRATOS_COLS = [
    "id_contrato", "proceso_de_compra", "estado_contrato", "sector", "orden", "rama",
    "entidad_centralizada", "codigo_entidad", "nit_entidad", "nombre_entidad", "departamento", "ciudad",
    "codigo_de_categoria_principal", "tipo_de_contrato", "modalidad_de_contratacion",
    "justificacion_modalidad_de", "fecha_de_firma", "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato", "duraci_n_del_contrato", "condiciones_de_entrega",
    "codigo_proveedor", "tipodocproveedor", "es_grupo", "es_pyme", "habilita_pago_adelantado",
    "liquidaci_n", "obligaci_n_ambiental", "obligaciones_postconsumo", "reversion",
    "origen_de_los_recursos", "destino_gasto", "valor_del_contrato", "saldo_cdp", "saldo_vigencia",
    "espostconflicto", "el_contrato_puede_ser_prorrogado", "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regal_as",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_", "recursos_de_credito",
    "recursos_propios", "dias_adicionados", "ultima_actualizacion",
]  # dias_adicionados se baja solo para auditar fuga; NO es feature.
ADICIONES = "cb9c-h8sn"
ADICIONES_COLS = ["identificador", "id_contrato", "tipo", "fecharegistro"]


def fetch(dataset, cols, where, dest, limit=None):
    token = os.environ.get("SOCRATA_APP_TOKEN")
    n, offset = 0, 0
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        while limit is None or n < limit:
            size = PAGE if limit is None else min(PAGE, limit - n)
            q = {"$select": ",".join(cols), "$where": where, "$order": ":id", "$limit": size, "$offset": offset}
            req = urllib.request.Request(f"{BASE}/{dataset}.json?{urllib.parse.urlencode(q)}")
            if token:
                req.add_header("X-App-Token", token)
            for attempt in range(5):
                try:
                    rows = json.load(urllib.request.urlopen(req, timeout=120))
                    break
                except Exception as e:
                    if attempt == 4:
                        raise
                    print(f"  reintento ({e})")
                    time.sleep(5 * (attempt + 1))
            if not rows:
                break
            w.writerows({c: r.get(c, "") for c in cols} for r in rows)
            n += len(rows)
            offset += len(rows)
            print(f"{dest.name}: {n} filas")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    fetch(CONTRATOS, CONTRATOS_COLS, "sector like 'Salud%' AND fecha_de_firma>='2017-01-01'",
          OUT / "contratos_salud.csv", a.limit)
    fetch(ADICIONES, ADICIONES_COLS, "tipo='Adicion en el valor'", OUT / "adiciones_valor.csv", a.limit)
