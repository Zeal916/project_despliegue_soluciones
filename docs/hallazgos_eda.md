# Hallazgos del EDA: contratos de obra en SECOP II (2019 a 2025)

Notebook: `notebooks/01_eda_obra.ipynb` · Figuras: `reports/figures/` · Datos: `src/ingest.py`, descarga del
7 de noviembre de 2026, versionados con DVC.

## 1. Datos

1. Universo: 40.621 contratos tipo "Obra" de Contratos Electrónicos (jbjy-vk9h) firmados entre 2019 y 2025.
2. Cobertura de los cruces:
   1. Procesos de Contratación (p6dx-8zbt): 100 %.
   2. Proveedores Registrados (qmzu-gj57): 66,6 %; faltan sobre todo personas jurídicas.
   3. Ofertas por Proceso (wi7w-2nvm): 69,2 % de los contratos de 2025; la tabla no cubre años anteriores.
   4. Garantías (gjp9-cutm): 1,1 %; la tabla publicada tiene 48.949 pólizas en total.
3. Variable objetivo: `y = 1` si el contrato aparece en Adiciones (cb9c-h8sn) con tipo "Adicion en el valor" o si
   `dias_adicionados > 0`. Tasa de 36,4 %: 10,5 % en valor y 28,3 % en tiempo.

## 2. Revisiones para el mockup

| # | Revisión | Hallazgo | Cambio sugerido al mockup | Elemento |
| --- | --- | --- | --- | --- |
| 1 | Balance de clases | 36,4 % (valor 10,5 %, tiempo 28,3 %); 29,7 % a 35,3 % entre 2019 y 2024 y 46,3 % en 2025. | KPI con tasa base y tasa por año; semáforo por percentil de riesgo. | A, H |
| 2 | Faltantes en variables de firma | Valor inicial 0,25 %, plazo inicial 9,6 %, condiciones de entrega 36,2 %, datos del proveedor 33,4 %. | Plazo, condiciones de entrega y datos del proveedor opcionales en el formulario. | G |
| 3 | Departamentos | 18,5 % a 50,6 % (n ≥ 50); Bogotá concentra el 28,7 % de los contratos con 38,6 %. | Barras ordenadas por tasa con n mínimo en lugar de mapa. | B |
| 4 | Modalidad | Licitación pública 51,8 %, menor cuantía 38,1 %, directa 32,4 %, mínima cuantía 26,1 %; 2 de 9 modalidades con menos de 1.000 contratos. | Agrupar variantes con su modalidad principal y mostrar el n. | C |
| 5 | Valor y plazo | Tasa de 14,9 % (decil 1) a 54,5 % (decil 10) del valor inicial, Spearman 0,25; plazo inicial 0,13. | Conservar el mapa de calor, construido con valor y plazo del proceso, y añadir la curva por deciles. | D |
| 6 | Mes de firma | Diciembre concentra el 18,2 % de las firmas; noviembre y diciembre tienen más adición en tiempo (31,8 % y 34,1 %) y menos en valor (8,6 % y 7,9 %). | Serie mensual de volumen y tasa por tipo de adición; el mes entra en la lectura sugerida. | E, K |
| 7 | Entidades | 2.378 entidades; las 10 mayores aportan el 22,8 % de los contratos con adición; tasa de 12,7 % (p10) a 60,8 % (p90) entre entidades con n ≥ 30. | Tabla con n ≥ 30, filtro por entidad y tasa histórica de la entidad. | F, J |
| 8 | Tiempo frente a valor | P(valor \| tiempo) = 8,5 % y P(tiempo \| valor) = 22,8 %; solo 977 contratos tienen ambas. | Dos probabilidades (tiempo y valor) y selector de tipo de adición. | H |
| 9 | Fuga | `estado_contrato` (AUC 0,86), fecha de fin (0,76), valor actual (0,66) y duración del contrato (0,65) son posteriores a la firma. | El formulario pide valor y plazo del proceso y excluye estado y días adicionados. | G, I |
| 10 | Magnitud | Una adición en valor por contrato (mediana); la adición en tiempo equivale al 50 % del plazo inicial (mediana). | KPI de extensión relativa del plazo en lugar de conteo de adiciones. | A |
| 11 | Objeto y financiación | Crédito (58,0 %) y regalías (44,4 %) superan a SGP (28,2 %); procesos con adición tardan más de publicación a adjudicación (26 frente a 19 días). | Fuente principal y segmento UNSPSC en filtros y formulario; fechas del proceso precargadas por ID. | G, filtros |

## 3. Hallazgos que cambian el diseño del modelo

1. `valor_del_contrato` incluye las adiciones: con adición en valor, la razón mediana frente al valor adjudicado es 1,29 y
   el percentil 90 es 1,50, igual al tope legal del 50 %. El valor al firmar se toma del precio base del proceso.
2. `duraci_n_del_contrato` y `fecha_de_fin_del_contrato` incorporan las prórrogas. El plazo al firmar se toma de la
   duración publicada del proceso.
3. Filtrar por estado terminado o cerrado reduce la tasa de 36,4 % a 16,9 % porque excluye los contratos "Modificado"
   (80,6 % de adición). La muestra se define por fecha de firma; solo se excluyen contratos con plazo inicial vigente
   (4,3 % en 2025 y menos de 1 % en los demás años).
4. La adición en tiempo sube de 13,5 % (2019) a 41,9 % (2025) dentro de todas las modalidades, mientras la adición en
   valor baja de 24,2 % a 7,6 %. Es un cambio en la práctica de registro que afecta la partición temporal.
5. El 29,0 % de los contratos sin adición registrada supera en más de 5 % su valor adjudicado, lo que indica
   subregistro en la tabla Adiciones.
6. Las respuestas al proceso (Procesos) coinciden con el conteo de Ofertas por Proceso en el 87,7 % de los contratos de
   2025 (Spearman 0,994) y cubren todo el periodo, por lo que reemplazan a Ofertas como variable de competencia.
7. La primera póliza se crea, en mediana, 302 días después de la firma y la tabla cubre el 1,1 % de los contratos.
   Garantías queda fuera del modelo mientras siga incompleta.
8. Los montos por fuente de recursos también incluyen las adiciones (mediana de 1,16 frente al valor inicial con
   adición en valor). Solo se usa la fuente principal como categoría.

## 4. Contraste con el estado del arte

1. Rodríguez Arévalo (2021) y Salazar Mejía (2024) usan el valor del contrato y plazos calculados con la fecha de fin,
   que incorporan las adiciones, y particiones aleatorias. Sus métricas (precisión de 0,92 y MAP@100 de 1,00)
   probablemente son optimistas para un uso al momento de la firma.
2. Salazar Mejía filtra por estado del contrato, que depende del desenlace; aquí la muestra se define por fecha de firma.
3. Se confirman el peso del valor, de la entidad y del ciclo fiscal, el menor riesgo de las entregas "a convenir" y la
   baja adición en valor de la contratación directa.
4. El conteo de adiciones en valor (Salazar Mejía) aporta poco en obra, donde la mediana es una adición por contrato.
5. Se suman variables derivadas de los antecedentes: fuente principal de recursos, segmento UNSPSC, días entre
   publicación y adjudicación, experiencia de la entidad y proveedor repetido.
6. Siguiendo a Reina Hidalgo (2026), el modelo solo prioriza la vigilancia, cada alerta lleva su explicación (SHAP) y
   revisión humana, y se vigilan las tasas de alerta por tipo de proveedor y departamento.

## 5. Implicaciones para el modelado

1. Modelo combinado y dos modelos por tipo de adición (tiempo y valor).
2. Variables: valor inicial (logaritmo), plazo inicial, modalidad agrupada, departamento, entidad, mes de firma,
   respuestas al proceso, adjudicado sobre precio base, días entre publicación y adjudicación, segmento UNSPSC, fuente
   principal, destino del gasto, condiciones de entrega, experiencia de la entidad, proveedor repetido, antigüedad del
   proveedor, pyme y tipo de documento, con indicadores de faltante.
3. Exclusiones: `estado_contrato`, `valor_del_contrato`, `duraci_n_del_contrato`, `fecha_de_fin_del_contrato`,
   `dias_adicionados`, montos por fuente y variables de ejecución (pagos, facturación, saldos, última actualización).
4. Partición temporal: entrenamiento 2019 a 2023, validación 2024 y prueba 2025, con métricas por año y recalibración
   con el año más reciente.
5. Entidad codificada por tasa con suavizado dentro de cada pliegue y evaluación con entidades no vistas.
6. Métricas: PR-AUC y precisión en k, con AUC-ROC como referencia.

## 6. Limitaciones

1. Subregistro probable de la adición en valor.
2. Cambio en el registro de días adicionados a lo largo del periodo.
3. Proveedores cubre dos tercios de los contratos y Garantías casi ninguno.
4. La adición es un indicador: no se conoce el monto adicionado.
5. Para el 6 % de los contratos que comparten proceso, el precio base corresponde a todo el proceso y no solo al
   contrato.
6. La fecha de inicio puede registrarse después de la firma; los días entre firma e inicio solo se usan si se confirma
   que se conocen al firmar.
