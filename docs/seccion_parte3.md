# Parte 3 – Datos, repositorios y exploración (texto para el reporte)

> Texto listo para pegar en el docx. Figuras sugeridas (límite de 10 páginas): `01_tasa_por_anio`, `05_valor_plazo`,
> `07_entidades`, `09_fuga_auc`. Las demás están en `reports/figures/` como soporte.

## Repositorios y versionado de datos

**Código (Git).** Repositorio en GitHub: https://github.com/Zeal916/project_despliegue_soluciones
Estructura: `src/` (ingesta y verificación de fuentes), `notebooks/` (EDA), `docs/` (hallazgos y evidencia),
`reports/figures/` (gráficas), `docker/` y `docker-compose.yml` (entorno reproducible con MLflow), `app/` (reservado para API y tablero).

**Datos (DVC).** Los datos se versionan con DVC y se almacenan en DagsHub:
https://dagshub.com/Zeal916/project_despliegue_soluciones. En Git solo se guardan los archivos `.dvc` (hash y tamaño);
los CSV viven en el remoto. Para reproducir:

```
git clone https://github.com/Zeal916/project_despliegue_soluciones.git
dvc pull                       # descarga los CSV versionados desde DagsHub
python src/ingest.py           # alternativa: regenerar desde datos.gov.co
```

## Conjuntos de datos

**Muestra incluida en la entrega.** Los CSV completos (unos 450 MB) están en DagsHub vía DVC. Para revisión sin descargarlos,
`data/sample/` contiene una muestra aleatoria reproducible (`src/make_sample.py`, semilla 42) de 20.000 contratos 2017–2025
y sus 2.285 adiciones (tasa de adición 26,6 % frente a 27,1 % en la población).

Fuente: datos abiertos de SECOP II (Colombia Compra Eficiente) en datos.gov.co, consultados por la API de Socrata
mediante `src/ingest.py`, que excluye datos personales (nombres, documentos, cuentas bancarias).

| Archivo | Origen | Filas | Contenido |
|---|---|---|---|
| `contratos_salud.csv` | Contratos Electrónicos (jbjy-vk9h), sector Salud y Protección Social, firmados desde 2017 | 800.011 | 45 columnas: entidad, ubicación, modalidad, tipo, fechas, plazo, valor, origen de los recursos, saldos presupuestales, proveedor (solo tipo de documento y código) |
| `adiciones_valor.csv` | Adiciones (cb9c-h8sn), tipo "Adicion en el valor" | 257.152 | Contrato, fecha de registro. Cubre todo el país; se cruza por `id_contrato` |

Descarga realizada el 24-oct-2026. Rango de firma: 7-feb-2017 a 23-oct-2026.

**Variable objetivo.** `y = 1` si el contrato tiene al menos una adición en valor (tabla Adiciones) o
días adicionados (`dias_adicionados > 0`).

**Contingencia de datos.** La tabla de contratos (jbjy-vk9h) quedó truncada en origen: devuelve solo 1.000 filas desde el 25-oct-2026
(antes 5,6 millones); las demás tablas siguen completas (evidencia en `docs/evidencia_caida_fuente.txt`, generada con
`src/check_source.py`). Esto impidió descargar el alcance de obra pública, por lo que el EDA se ejecutó sobre la descarga
previa del sector Salud, con la misma variable objetivo y la misma guía de revisiones. El cuaderno
pasa a obra cambiando el filtro de `ingest.py` cuando la fuente se restablezca.

## Exploración de los datos

Cuaderno: `notebooks/01_eda_salud.ipynb`. Muestra analizada: 667.817 contratos firmados entre 2017 y 2025
(se excluye 2026 porque sus contratos aún no han tenido tiempo de recibir adiciones).

**Balance de clases.** El 27,1 % de los contratos registra alguna adición (22,0 % en tiempo, 7,1 % en valor). La tasa
no es estable: oscila entre 20 % y 43 % según el año de firma (Fig. 1). Las adiciones en tiempo casi no se diligenciaban
antes de 2019 (0,2 % en 2017–2018, 18,5 % en 2019), lo que respalda el corte de 2019 en adelante y exige validación temporal.

**Valor y plazo.** La tasa de adición crece con el valor del contrato, de 4,6 % en el decil más bajo a 37 % en el noveno
(Spearman 0,22). El plazo tiene un efecto menor (Spearman 0,05), aunque en valores altos los plazos de más de un año
elevan la tasa (Fig. 2).

**Modalidad y estacionalidad.** Dominan la contratación de régimen especial (446 mil contratos, tasa 31 %) y la
directa (192 mil, 18 %); 6 de las 13 modalidades tienen menos de 1.000 contratos. La tasa es más alta de enero a marzo
(32–33 %) y baja en noviembre (15 %).

**Concentración.** 633 entidades; las 10 mayores acumulan el 66 % de los contratos con adición, y Bogotá concentra el 44 %
de los contratos con la tasa departamental más alta (40 %) (Fig. 3). Existe el riesgo de que un modelo aprenda
principalmente qué entidad firma.

**Adición en tiempo vs. en valor.** Son fenómenos distintos: el 28 % de los contratos con adición en valor también la
tienen en tiempo, pero solo el 9 % de los que tienen adición en tiempo la tienen en valor. Esto respalda ofrecer ambas
probabilidades en el tablero.

**Calidad de datos.** Valor, modalidad, tipo y origen de recursos no tienen nulos; el plazo no está definido en 11,8 %,
el pago adelantado en 12,7 % y las condiciones de entrega en 22,6 %. Hay 14 contratos con más de 5 años de días
adicionados (posible error de digitación) y valores de contrato extremos (hasta 2·10¹⁴).

**Fuga de información.** Se calculó el AUC de cada variable por separado contra `y` (Fig. 4).
`dias_adicionados` (0,91, parte del objetivo) y `estado_contrato` (0,89) delatan el desenlace y se excluyen: el estado
"Modificado" tiene una tasa de 69 %. `saldo_cdp`, `saldo_vigencia` y `ultima_actualizacion` no aportan señal (≈0,50).
La entidad (0,76), el departamento (0,67) y el valor (0,64) son informativas y legítimas al momento de la firma.

**Implicaciones para el modelado.** (i) Validación temporal por fecha de firma, no aleatoria. (ii) Muestra definida por
año y no por estado. (iii) Métricas de priorización (PR-AUC y precisión en k) por el desbalance y la capacidad de
revisión limitada. (iv) Evaluar con entidades no vistas o sin las 10 mayores para medir generalización real.

**Limitaciones.** Muestra de Salud y no de obra; sin ofertas, garantías ni proveedores (tablas aparte, pendientes);
la adición es un indicador, no se conoce el monto adicionado.
