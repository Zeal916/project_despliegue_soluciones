"""Alternativa a la tabla de Contratos Electrónicos (truncada): contratos de OBRA de SECOP II desde SECOP Integrado (rpmr-utcd)
y señales de adición (valor / prórroga) desde la tabla Adiciones, por el texto de la descripción.

Uso: python src/ingest_obra.py [--limit N]
Sin datos personales: se excluyen nombre y documento del contratista, objeto y URL.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import OUT, fetch  # noqa: E402

INTEGRADO = "rpmr-utcd"
OBRA_COLS = [
    "numero_del_contrato", "numero_de_proceso", "estado_del_proceso", "nivel_entidad", "codigo_entidad_en_secop",
    "nombre_de_la_entidad", "nit_de_la_entidad", "departamento_entidad", "municipio_entidad", "modalidad_de_contrataci_n",
    "tipo_de_contrato", "fecha_de_firma_del_contrato", "fecha_inicio_ejecuci_n", "fecha_fin_ejecuci_n", "valor_contrato",
    "origen", "tipo_documento_proveedor",
]
OBRA_WHERE = ("origen='SECOPII' AND tipo_de_contrato='Obra' AND "
              "fecha_de_firma_del_contrato between '2019-01-01T00:00:00' and '2025-12-31T23:59:59'")
ADIC = "cb9c-h8sn"
ADIC_COLS = ["id_contrato", "tipo", "fecharegistro"]
SENALES = {
    "adic_senal_prorroga.csv": "upper(descripcion) like '%PRORROG%' OR upper(descripcion) like '%PRÓRROG%'",
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    fetch(INTEGRADO, OBRA_COLS, OBRA_WHERE, OUT / "contratos_obra_integrado.csv", a.limit)
    for nombre, where in SENALES.items():
        fetch(ADIC, ADIC_COLS, where, OUT / nombre, a.limit)
