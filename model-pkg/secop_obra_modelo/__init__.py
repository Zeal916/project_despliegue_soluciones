"""Modelo de riesgo de adición en contratos de obra pública (SECOP II)."""
from secop_obra_modelo.predict import (VERSION, Contrato, estado,
                                       predecir_contrato, predecir_lote)

__version__ = VERSION
__all__ = ["Contrato", "estado", "predecir_contrato", "predecir_lote"]
