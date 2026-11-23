# secop_obra_modelo

Paquete del modelo de riesgo de adición en contratos de obra de SECOP II. Contiene los tres modelos CatBoost del
modelo ganador (`y`, `y_tiempo`, `y_valor`) con su recalibración de Platt, las probabilidades de los contratos de 2025
para calcular el percentil, 300 contratos de entrenamiento como fondo para SHAP y las tasas por entidad. No necesita el
resto del repositorio ni los datos.

## 1. Instalación

```bash
pip install model-pkg/dist/secop_obra_modelo-1.0.0-py3-none-any.whl
```

En el Dockerfile de la API:

```dockerfile
COPY model-pkg/dist/secop_obra_modelo-1.0.0-py3-none-any.whl /tmp/
RUN pip install /tmp/secop_obra_modelo-1.0.0-py3-none-any.whl
```

## 2. Uso

```python
from secop_obra_modelo import estado, predecir_contrato, predecir_lote

estado()                                   # GET /health
predecir_contrato(contrato, factores=True, n=6)   # POST /predict
predecir_lote(lista_de_contratos)          # POST /predict/lote -> {"resultados": ...}
```

Las tres funciones devuelven diccionarios o listas listos para JSON, con las claves que espera el tablero
(`app/comun.py`). Un contrato es un diccionario con las variables conocidas al firmar; todas son opcionales:

| Campo | Tipo | Ejemplo |
| --- | --- | --- |
| `id_contrato` | texto | `CO1.PCCNTR.0001` |
| `valor_inicial` (o `log_valor_inicial`) | número, en pesos (o su log10) | `850000000` |
| `plazo_inicial` | número, en días | `180` |
| `respuestas` | número | `3` |
| `inicial_sobre_base` | número | `0.98` |
| `dias_publicacion_adjudicacion` | número | `35` |
| `nombre_entidad` | texto | Calcula la tasa y los contratos previos de la entidad |
| `tasa_entidad`, `previos_entidad` | número | Si llegan, no se calculan; `tasa_entidad` vacía se imputa |
| `antiguedad_prov` | número, en años | `4.5` |
| `modalidad`, `departamento`, `segmento_unspsc`, `destino_gasto`, `condiciones_de_entrega`, `es_pyme`, `mes` | texto o número | `Licitación pública`, `Antioquia`, `72`, `Inversión`, `A convenir`, `No`, `12` |

Un campo con tipo inválido lanza `pydantic.ValidationError`; la API debe responder 422. `Contrato` es el esquema
pydantic, reutilizable en FastAPI.

## 3. Regenerar el paquete

Desde la raíz del repositorio, con el entorno de `docs/modelos.md`:

```bash
python src/features.py           # tabla de modelado
python src/modelo.py --ganador   # models/modelo_*.joblib
python model-pkg/entrenar.py     # artefactos y comprobación frente a src/modelo.py
pip wheel ./model-pkg --no-deps -w model-pkg/dist
pip install model-pkg/dist/secop_obra_modelo-1.0.0-py3-none-any.whl pytest
python -m pytest model-pkg/tests
```

Si cambia el modelo, subir el número en `secop_obra_modelo/VERSION`.
