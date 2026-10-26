# Parte 3 – Datos, repositorios y exploración (texto para el reporte)

> Texto listo para pegar en el docx. Figuras sugeridas (límite de 10 páginas), de `reports/figures_snapshot/`:
> `01_tasa_por_anio`, `05_valor_plazo`, `09_fuga_auc`. Las de Salud (`reports/figures/`) y las demás quedan como soporte.

## Repositorios y versionado de datos

**Código (Git).** https://github.com/Zeal916/project_despliegue_soluciones
Estructura: `src/` (ingesta, verificación de fuentes y muestra), `notebooks/` (EDA), `docs/` (hallazgos y evidencia),
`reports/` (figuras), `docker/` y `docker-compose.yml` (entorno reproducible con MLflow), `app/` (reservado para API y tablero).

**Datos (DVC).** Los datos se versionan con DVC y se almacenan en DagsHub:
https://dagshub.com/Zeal916/project_despliegue_soluciones. En Git solo quedan los archivos `.dvc` (hash y tamaño). Para reproducir:

```
git clone https://github.com/Zeal916/project_despliegue_soluciones.git
dvc pull                       # descarga los CSV versionados desde DagsHub
python src/ingest.py           # alternativa: regenerar desde datos.gov.co
```

## Conjuntos de datos

Fuente: datos abiertos de SECOP II (Colombia Compra Eficiente) en datos.gov.co, consultados por la API de Socrata
con `src/ingest.py`, que excluye datos personales (nombres, documentos, correos, cuentas bancarias).

| Archivo | Origen | Filas | Uso |
|---|---|---|---|
| `contratos_snapshot_20261026_0203Z.csv` | Contratos Electrónicos (jbjy-vk9h), instantánea de la tabla tal como estaba el 26-oct-2026 02:03 UTC | 1.000 | **EDA principal** (todos los sectores, firmas 2018–2026) |
| `adiciones_valor.csv` | Adiciones (cb9c-h8sn), tipo "Adicion en el valor" | 257.152 | Se cruza por `id_contrato` con los contratos |
| `contratos_salud.csv` | Contratos Electrónicos, sector Salud, firmados desde 2017, descargados el 24-oct-2026 | 800.011 | **EDA complementario** (volumen suficiente para contrastar) |

En el repositorio se incluye además una muestra reproducible de 20.000 contratos de Salud (`data/sample/`, `src/make_sample.py`, semilla 42).

**Variable objetivo.** `y = 1` si el contrato tiene al menos una adición en valor (tabla Adiciones) o días adicionados
(`dias_adicionados > 0`).

## Nota sobre la disponibilidad de la fuente

Cuando abordamos el proyecto, la tabla de Contratos Electrónicos contaba con otro número de filas: al consultarla el
24-oct-2026 tenía 5.658.404 registros. El 25-oct-2026 pasó a devolver solo 1.000, y la propia fuente registra
modificaciones de la tabla el 25-oct (05:48 UTC) y el 26-oct (01:14 UTC), es decir, **se está actualizando justo en el
momento de elaborar este informe**. Las demás tablas (procesos, adiciones, garantías, proveedores y ofertas) permanecen
completas. La disponibilización de este conjunto a última hora está fuera de nuestro control.

Por ello el EDA principal se hizo sobre las 1.000 filas disponibles, versionadas y fechadas en DVC, y se complementó con la
descarga previa del sector Salud. Si la tabla no se repone, el trabajo continuará con los otros conjuntos de datos
descritos en la definición del problema. Evidencia: `docs/evidencia_caida_fuente.txt` y `docs/evidencia_fuente_20261026_0204Z.txt`
(generadas con `src/check_source.py`) y capturas de la página del conjunto.

## Exploración de los datos

Cuaderno: `notebooks/02_eda_snapshot.ipynb` (instantánea) y `notebooks/01_eda_salud.ipynb` (Salud); es el mismo código con
umbrales de tamaño mínimo ajustados. Se analizan los contratos firmados entre 2017 y 2025 (se excluye 2026 porque aún no han
tenido tiempo de recibir adiciones): 810 en la instantánea y 667.817 en Salud.
**Con 1.000 filas, los resultados son indicativos, no concluyentes; por eso se contrastan con Salud.**

| Indicador | Instantánea (810) | Salud (667.817) |
|---|---|---|
| Tasa de adición `y` | 18,6 % | 27,1 % |
| En tiempo / en valor | 15,6 % / 3,8 % | 22,0 % / 7,1 % |
| Tasa en el estado "Modificado" | 60 % | 69 % |
| Spearman valor ~ `y` / plazo ~ `y` | 0,22 / 0,11 | 0,22 / 0,05 |
| Tasa por cuantil de valor (más bajo → más alto) | 10 % → 35 % (quintiles) | 5 % → 37 % (deciles) |
| Contratos de Bogotá | 42 % | 44 % |
| Entidades que concentran las adiciones | 10 mayores: 40 % (370 entidades) | 10 mayores: 66 % (633) |
| Perfil tiempo/valor: P(valor \| tiempo) / P(tiempo \| valor) | 5 % / 19 % | 9 % / 28 % |
| Nulos en plazo / pago adelantado / condiciones de entrega | 8,1 % / 9,6 % / 24,8 % | 11,8 % / 12,7 % / 22,6 % |

**Lectura conjunta.**
- **Desbalance:** entre el 19 % y el 27 % de los contratos recibe alguna adición; la mayoría de las adiciones son en tiempo.
  La tasa cambia mucho según el año de firma (Fig. 1), por lo que el modelo debe validarse con partición temporal.
  Las adiciones en tiempo casi no se diligenciaban antes de 2019 (0,2 % en Salud en 2017–2018), lo que respalda el corte de 2019.
- **Valor y plazo:** la probabilidad de adición crece con el valor del contrato en ambas muestras (Fig. 2); el plazo pesa menos.
- **Modalidad y entidad:** dominan la contratación directa y el régimen especial. Pocas entidades, sobre todo las
  subredes de salud de Bogotá, concentran la mayoría de las adiciones; un modelo podría aprender principalmente qué entidad firma.
- **Estacionalidad:** en Salud es marcada (enero–marzo 32–33 %, noviembre 15 %); en la instantánea, con pocos contratos por mes,
  no se puede concluir.
- **Contratos de obra:** la instantánea trae 9 contratos de obra (tasa 11 %) y Salud 1.092 (tasa 32 %); son pocos para
  concluir, y es el principal vacío frente al alcance definido.
- **Fuga de información** (Fig. 3, AUC de cada variable contra `y`; instantánea / Salud): `dias_adicionados` (0,92 / 0,91) y
  `estado_contrato` (0,88 / 0,89) delatan el desenlace y se excluyen. `saldo_cdp` y `saldo_vigencia` no aportan señal en Salud.
  La entidad (0,68 / 0,76), el valor (0,66 / 0,64) y el departamento (0,59 / 0,67) son informativas y legítimas al firmar.
- **Calidad de datos:** 8 contratos de la instantánea sin fecha de firma válida; en Salud, 14 con más de 5 años de días
  adicionados (posible error de digitación) y valores extremos de contrato (hasta 2·10¹⁴).

**Implicaciones para el modelado.** (i) Validación temporal por fecha de firma. (ii) Muestra definida por año y no por estado.
(iii) Métricas de priorización (PR-AUC y precisión en k) por el desbalance y la capacidad de revisión limitada.
(iv) Evaluar con entidades no vistas o sin las 10 mayores.

**Limitaciones.** Instantánea pequeña y de varios sectores; la muestra de Salud no es de obra; sin ofertas, garantías ni
proveedores todavía (tablas aparte, disponibles); la adición es un indicador, no se conoce el monto adicionado.
