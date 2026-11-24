"""Pruebas de la API: python -m pytest tests (requiere el .whl, fastapi y httpx)."""
import pytest
from fastapi.testclient import TestClient

from app.api import MAX_LOTE, app

CONTRATO = {
    "id_contrato": "CO1.PCCNTR.0001",
    "valor_inicial": 850_000_000,
    "plazo_inicial": 180,
    "respuestas": 3,
    "nombre_entidad": "ENTIDAD SIN HISTORIA",
    "modalidad": "Licitación pública",
    "departamento": "Antioquia",
    "segmento_unspsc": "72",
    "mes": 12,
}


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_predict_con_factores(cliente):
    r = cliente.post("/predict", json=CONTRATO, params={"n": 4})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["id_contrato"] == CONTRATO["id_contrato"]
    assert cuerpo["nivel_alerta"] in {"alta", "media", "baja"}
    assert all(len(f) == 4 for f in cuerpo["factores"].values())


def test_predict_sin_factores(cliente):
    r = cliente.post("/predict", json=CONTRATO,
                     params={"factores": "false"})
    assert r.status_code == 200 and r.json()["factores"] == {}


def test_tipo_invalido_422(cliente):
    r = cliente.post("/predict", json={**CONTRATO, "plazo_inicial": "seis"})
    assert r.status_code == 422


def test_n_fuera_de_rango_422(cliente):
    assert cliente.post("/predict", json=CONTRATO,
                        params={"n": 0}).status_code == 422


def test_codigo_decimal_igual_a_texto(cliente):
    def p(segmento):
        r = cliente.post("/predict", json={**CONTRATO, "segmento_unspsc":
                                           segmento}, params={"factores": "false"})
        return r.json()["probabilidades"]["y"]
    assert p(72.0) == pytest.approx(p("72"))


def test_null_explicito_se_conserva(cliente):
    """tasa_entidad: null se imputa; omitida se calcula por la entidad."""
    def p(contrato):
        return cliente.post("/predict", json=contrato,
                            params={"factores": "false"}).json()
    con_null = p({**CONTRATO, "tasa_entidad": None})
    assert con_null["tasa_entidad_usada"] is None
    assert p(CONTRATO)["tasa_entidad_usada"] is not None


def test_lote_coincide_con_individual(cliente):
    otro = {**CONTRATO, "id_contrato": "2", "respuestas": 1}
    r = cliente.post("/predict/lote", json={"contratos": [CONTRATO, otro]})
    assert r.status_code == 200
    res = r.json()["resultados"]
    uno = cliente.post("/predict", json=CONTRATO,
                       params={"factores": "false"}).json()
    assert [x["id_contrato"] for x in res] == ["CO1.PCCNTR.0001", "2"]
    assert res[0]["p_y"] == pytest.approx(uno["probabilidades"]["y"])


def test_lote_vacio_y_limite(cliente):
    assert cliente.post("/predict/lote", json={"contratos": []}
                        ).json() == {"resultados": []}
    grande = {"contratos": [{}] * (MAX_LOTE + 1)}
    assert cliente.post("/predict/lote", json=grande).status_code == 422
