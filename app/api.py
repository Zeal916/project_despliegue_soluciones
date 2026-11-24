"""API de riesgo de adición en contratos de obra de SECOP II.

Sirve las predicciones del paquete secop_obra_modelo con las rutas que
consume el tablero (app/comun.py):

1. GET  /health        disponibilidad de los modelos.
2. POST /predict       un contrato: probabilidades, percentiles, alerta y
                       factores SHAP (?factores=true&n=6).
3. POST /predict/lote  {"contratos": [...]} -> {"resultados": [...]}.

Ejecución local: uvicorn app.api:app --port 8000 (documentación en /docs).
"""
from contextlib import asynccontextmanager

import secop_obra_modelo as modelo
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

MAX_LOTE = 5000  # el tablero envía bloques de este tamaño


class Contrato(modelo.Contrato):
    """Contrato del paquete; un código numérico que llega como decimal
    (72.0) se pasa a entero para que coincida con la categoría "72"."""

    @field_validator("segmento_unspsc", "mes", mode="before")
    @classmethod
    def _entero(cls, v):
        return int(v) if isinstance(v, float) and v.is_integer() else v


class Lote(BaseModel):
    contratos: list[Contrato] = Field(max_length=MAX_LOTE)


@asynccontextmanager
async def arranque(_):
    # Carga los modelos y el explicador SHAP antes de la primera petición.
    if modelo.estado()["estado"] == "ok":
        modelo.predecir_contrato({}, n=1)
    yield


app = FastAPI(title="API de riesgo de adición en obra pública (SECOP II)",
              version=modelo.__version__, lifespan=arranque)


@app.exception_handler(ValidationError)
async def _invalido(_: Request, e: ValidationError):
    return JSONResponse(status_code=422, content={
        "detail": e.errors(include_url=False, include_context=False)})


def _campos(contrato: Contrato) -> dict:
    # Solo los campos enviados: un null explícito (p. ej. tasa_entidad) se
    # conserva para que el modelo lo impute en lugar de recalcularlo.
    return contrato.model_dump(exclude_unset=True)


@app.get("/health")
def health():
    e = modelo.estado()
    return JSONResponse(e, status_code=200 if e["estado"] == "ok" else 503)


@app.post("/predict")
def predict(contrato: Contrato,
            factores: bool = True,
            n: int = Query(6, ge=1, le=15)):
    return modelo.predecir_contrato(_campos(contrato), factores=factores, n=n)


@app.post("/predict/lote")
def predict_lote(lote: Lote):
    return {"resultados": modelo.predecir_lote(
        [_campos(c) for c in lote.contratos])}
