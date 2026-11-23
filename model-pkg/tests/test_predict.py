"""Pruebas del paquete instalado: python -m pytest model-pkg/tests"""
import pytest
from pydantic import ValidationError

from secop_obra_modelo import estado, predecir_contrato, predecir_lote

CONTRATO = {
    "id_contrato": "CO1.PCCNTR.0001",
    "valor_inicial": 850_000_000,
    "plazo_inicial": 180,
    "respuestas": 3,
    "inicial_sobre_base": 0.98,
    "dias_publicacion_adjudicacion": 35,
    "nombre_entidad": "ENTIDAD SIN HISTORIA",
    "antiguedad_prov": 4.5,
    "modalidad": "Licitación pública",
    "departamento": "Antioquia",
    "segmento_unspsc": 72,
    "destino_gasto": "Inversión",
    "condiciones_de_entrega": "A convenir",
    "es_pyme": "No",
    "mes": 12,
}


def test_estado():
    e = estado()
    assert e["estado"] == "ok"
    assert e["anio_referencia"] == 2025
    assert e["contratos_referencia"] > 0


def test_predecir_contrato():
    r = predecir_contrato(CONTRATO, n=4)
    assert r["id_contrato"] == CONTRATO["id_contrato"]
    assert all(0 < p < 1 for p in r["probabilidades"].values())
    assert all(0 <= p <= 1 for p in r["percentiles"].values())
    assert r["riesgo_total"] == max(r["probabilidades"].values())
    assert r["nivel_alerta"] in {"alta", "media", "baja"}
    assert r["alerta"] == (r["percentil"] >= 0.90)
    assert r["entidad_con_historia"] is False
    assert all(len(f) == 4 for f in r["factores"].values())


def test_contrato_vacio_usa_imputacion():
    r = predecir_contrato({}, factores=False)
    assert 0 < r["probabilidades"]["y"] < 1
    assert r["factores"] == {}


def test_tipo_invalido():
    with pytest.raises(ValidationError):
        predecir_contrato({**CONTRATO, "plazo_inicial": "seis meses"})


def test_lote_coincide_con_individual():
    lote = predecir_lote([CONTRATO, {**CONTRATO, "id_contrato": "2",
                                     "respuestas": 1}])
    uno = predecir_contrato(CONTRATO, factores=False)
    assert len(lote) == 2
    assert lote[0]["p_y"] == pytest.approx(uno["probabilidades"]["y"])
    assert lote[0]["percentil"] == pytest.approx(uno["percentil"])
    assert predecir_lote([]) == []
