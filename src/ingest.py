"""Descarga los datos de SECOP II del proyecto (datos.gov.co, API Socrata).

Archivos generados en data/raw/:
1. contratos_obra.csv: contratos tipo Obra firmados entre 2019 y 2025
   (Contratos Electrónicos, jbjy-vk9h).
2. adiciones_valor.csv: adiciones en valor de esos contratos
   (Adiciones, cb9c-h8sn).
3. procesos_obra.csv: procesos de compra de esos contratos
   (Procesos de Contratación, p6dx-8zbt).
4. ofertas_obra.csv: ofertas distintas por proceso de los contratos firmados
   en 2025 (Ofertas por Proceso, wi7w-2nvm, que solo cubre 2025 y 2026).
5. garantias_obra.csv: pólizas de esos contratos (Garantías, gjp9-cutm).
6. proveedores_obra.csv: proveedores adjudicatarios
   (Proveedores Registrados, qmzu-gj57).

Uso: python src/ingest.py [--limit N]   (N limita los contratos; pruebas)
Opcional: SOCRATA_APP_TOKEN en el entorno para evitar limitación de peticiones.
Se excluyen datos personales: nombres, documentos, cuentas, correos,
teléfonos y direcciones.
"""
import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://www.datos.gov.co/resource"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
PAGE = 50_000
LOTE = 200

CONTRATOS = "jbjy-vk9h"
CONTRATOS_COLS = [
    "id_contrato", "proceso_de_compra", "codigo_entidad", "nombre_entidad",
    "departamento", "ciudad", "orden", "sector", "rama",
    "entidad_centralizada", "estado_contrato",
    "codigo_de_categoria_principal", "tipo_de_contrato",
    "modalidad_de_contratacion", "justificacion_modalidad_de",
    "fecha_de_firma", "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato", "duraci_n_del_contrato",
    "condiciones_de_entrega", "codigo_proveedor", "tipodocproveedor",
    "es_grupo", "es_pyme", "habilita_pago_adelantado", "liquidaci_n",
    "obligaci_n_ambiental", "obligaciones_postconsumo", "reversion",
    "origen_de_los_recursos", "destino_gasto", "valor_del_contrato",
    "valor_de_pago_adelantado", "espostconflicto",
    "el_contrato_puede_ser_prorrogado",
    "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regal_as",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_",
    "recursos_de_credito", "recursos_propios",
    # Variables de ejecución: solo para la variable objetivo y la auditoría
    # de fuga de información. No son variables explicativas.
    "dias_adicionados", "fecha_de_notificaci_n_de_prorrogaci_n",
    "valor_facturado", "valor_pagado", "valor_pendiente_de_ejecucion",
    "saldo_cdp", "saldo_vigencia", "ultima_actualizacion",
]
OBRA_WHERE = (
    "tipo_de_contrato = 'Obra' AND fecha_de_firma between "
    "'2019-01-01T00:00:00' and '2025-12-31T23:59:59'"
)

ADICIONES = "cb9c-h8sn"
ADICIONES_COLS = ["identificador", "id_contrato", "tipo", "fecharegistro"]

PROCESOS = "p6dx-8zbt"
PROCESOS_COLS = [
    "id_del_portafolio", "id_del_proceso", "fase",
    "estado_del_procedimiento", "adjudicado", "fecha_de_publicacion_del",
    "fecha_adjudicacion", "precio_base", "duracion", "unidad_de_duracion",
    "proveedores_invitados", "proveedores_que_manifestaron",
    "respuestas_al_procedimiento", "proveedores_unicos_con",
    "numero_de_lotes", "valor_total_adjudicacion",
]

OFERTAS = "wi7w-2nvm"
OFERTAS_COLS = [
    "id_del_proceso_de_compra",
    "count(distinct identificador_de_la_oferta) as n_ofertas",
]

GARANTIAS = "gjp9-cutm"
GARANTIAS_COLS = [
    "id_contrato", "tipopoliza", "subtipopoliza", "estado", "valor",
    "fechadecreacionpoliza", "fechafinpoliza",
]

PROVEEDORES = "qmzu-gj57"
PROVEEDORES_COLS = [
    "codigo", "es_entidad", "es_grupo", "esta_activa", "fecha_creacion",
    "pais", "departamento", "tipo_empresa", "espyme", "tama_o_entidad",
    "codigo_categoria_principal",
]


def leer(req, intentos=5):
    """Ejecuta la petición con reintentos y espera creciente."""
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.load(resp)
        except (OSError, ValueError) as err:
            if i == intentos - 1:
                raise
            print(f"  reintento {i + 1}: {err}")
            time.sleep(5 * (i + 1))


def query(dataset, select, where, group=None, limit=None):
    """Itera las filas de una consulta SoQL en páginas de PAGE filas."""
    token = os.environ.get("SOCRATA_APP_TOKEN")
    offset = 0
    while limit is None or offset < limit:
        size = PAGE if limit is None else min(PAGE, limit - offset)
        params = {
            "$select": ", ".join(select), "$where": where,
            "$order": group or ":id", "$limit": size, "$offset": offset,
        }
        if group:
            params["$group"] = group
        url = f"{BASE}/{dataset}.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        if token:
            req.add_header("X-App-Token", token)
        rows = leer(req)
        yield from rows
        if len(rows) < size:
            return
        offset += size


def query_en_lotes(dataset, select, llave, valores, group=None):
    """Consulta por lotes de LOTE valores de la llave (cláusula IN)."""
    valores = sorted(set(valores) - {""})
    for i in range(0, len(valores), LOTE):
        lista = ", ".join(
            "'{}'".format(v.replace("'", "''")) for v in valores[i:i + LOTE]
        )
        yield from query(dataset, select, f"{llave} in ({lista})", group)


def guardar(filas, select, destino):
    """Escribe las filas en CSV con los alias de la consulta como columnas."""
    cols = [s.split(" as ")[-1] for s in select]
    n = 0
    with open(destino, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for n, fila in enumerate(filas, 1):
            writer.writerow(fila)
    print(f"{destino.name}: {n:,} filas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    limit = parser.parse_args().limit
    OUT.mkdir(parents=True, exist_ok=True)

    contratos = list(query(CONTRATOS, CONTRATOS_COLS, OBRA_WHERE,
                           limit=limit))
    guardar(contratos, CONTRATOS_COLS, OUT / "contratos_obra.csv")
    ids = {c["id_contrato"] for c in contratos}
    procesos = {c.get("proceso_de_compra", "") for c in contratos}
    procesos_2025 = {
        c.get("proceso_de_compra", "") for c in contratos
        if c.get("fecha_de_firma", "") >= "2025"
    }
    proveedores = {c.get("codigo_proveedor", "") for c in contratos}

    adiciones = query(ADICIONES, ADICIONES_COLS,
                      "tipo = 'Adicion en el valor'")
    guardar((a for a in adiciones if a.get("id_contrato") in ids),
            ADICIONES_COLS, OUT / "adiciones_valor.csv")
    guardar(query_en_lotes(PROCESOS, PROCESOS_COLS, "id_del_portafolio",
                           procesos),
            PROCESOS_COLS, OUT / "procesos_obra.csv")
    guardar(query_en_lotes(OFERTAS, OFERTAS_COLS, "id_del_proceso_de_compra",
                           procesos_2025, group="id_del_proceso_de_compra"),
            OFERTAS_COLS, OUT / "ofertas_obra.csv")
    garantias = query(GARANTIAS, GARANTIAS_COLS, "1 = 1")
    guardar((g for g in garantias if g.get("id_contrato") in ids),
            GARANTIAS_COLS, OUT / "garantias_obra.csv")
    guardar(query_en_lotes(PROVEEDORES, PROVEEDORES_COLS, "codigo",
                           proveedores),
            PROVEEDORES_COLS, OUT / "proveedores_obra.csv")
