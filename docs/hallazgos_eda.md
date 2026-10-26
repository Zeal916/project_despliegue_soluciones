# Hallazgos del EDA (muestra Salud, 2017–2025)

Cuaderno: `notebooks/01_eda_salud.ipynb` · Figuras: `reports/figures/` · Fecha: 2026-10-25

**Contexto de datos.** La tabla `SECOP II – Contratos Electrónicos` (jbjy-vk9h) quedó fuera de servicio en origen
(1.000 filas desde el 24-oct-2026; las demás tablas siguen completas). El EDA usa la descarga previa del sector Salud:
800.011 contratos firmados desde 2017 (667.817 entre 2017 y 2025 tras excluir 2026). Los hallazgos de obra quedan
pendientes hasta que la fuente se recupere; el cuaderno cambia de sector con un filtro.

**Objetivo `y`** = adición en valor (tabla Adiciones) **o** en tiempo (`dias_adicionados > 0`).

## Respuesta a la tabla de 9 revisiones

| # | Revisión | Hallazgo | Cambio sugerido al mockup |
|---|---|---|---|
| 1 | Tasa global / balance | `y` = **27,1 %** (valor 7,1 %, tiempo 22,0 %). Desbalance moderado, no extremo. Varía mucho por año (20–43 % entre 2018 y 2025). | KPI muestra la tasa base y la tasa por año; semáforo por **percentil de riesgo** (A, H). |
| 2 | Nulos en variables de firma | Valor, modalidad, tipo y origen sin nulos; `plazo` 11,8 %, `pago adelantado` 12,7 %, `condiciones de entrega` 22,6 % "No definido". Ofertas, garantías y proveedores aún no descargados. | Marcar plazo y condiciones de entrega como **opcionales** en el formulario (G). |
| 3 | Departamentos | Tasa entre 9 % y 40 %, pero **Bogotá concentra 297 mil de 668 mil contratos** y tiene la tasa más alta (40 %). | Mapa poco informativo; usar **barras de departamentos con n ≥ 500** y nota de concentración (B). |
| 4 | Modalidad | Dominan *régimen especial* (446 mil contratos, tasa 31 %) y *contratación directa* (192 mil, tasa 18 %). 6 de 13 categorías tienen < 1.000 contratos. | **Agrupar** modalidades pequeñas en "Otras" y mostrar el n (C). |
| 5 | Valor y plazo | Relación **creciente con el valor**: 4,6 % (decil 1) a 37 % (decil 9); Spearman 0,22. El plazo pesa menos (0,05), aunque plazos > 365 días suben la tasa en deciles altos. | El mapa de calor es informativo: conservar D, añadir curva por deciles de valor. |
| 6 | Estacionalidad | Enero–marzo 32–33 %, junio–agosto ~20 %, noviembre 15 %. Patrón **marcado**. | Mantener E y añadir el mes como factor en K. |
| 7 | Entidades | 633 entidades; **top 10 = 66 % de los contratos con adición**, top 100 = 95 %. Entre entidades con n ≥ 200: p10 1,4 %, mediana 12 %, p90 33 %. Dominan las Subredes de Bogotá. | Priorizar F con mínimo de contratos y filtro por entidad. Riesgo de que el modelo aprenda la entidad. |
| 8 | Tiempo vs valor | Perfiles distintos: P(valor \| tiempo) = 9 %, P(tiempo \| valor) = 28 %. Tiempo: 22 %; valor: 7 %. Régimen especial 25 % en tiempo, contratación directa 3 % en valor. | **Selector de tipo de adición** y dos probabilidades (H). |
| 9 | Fuga | `dias_adicionados` (AUC 0,91, es parte del objetivo) y `estado_contrato` (0,89) son **fuga**. `saldo_cdp`, `saldo_vigencia` y `ultima_actualizacion` no tienen señal (≈0,50). `nombre_entidad` 0,76, `departamento` 0,67 y `valor` 0,64 son legítimas pero dependen del contexto. | Excluir estado y días adicionados del modelo y del formulario (G, I). |

## Hallazgos adicionales que afectan el diseño

1. **El campo de adiciones en tiempo no se diligenciaba antes de 2019:** 0,2 % en 2017–2018, 18,5 % en 2019. Esto respalda
   el corte de **2019 en adelante** del alcance. Las adiciones en valor muestran un cambio de registro similar: 28–29 %
   en 2018–2019 y 3–8 % después.
2. **La tasa no es estable en el tiempo** (picos en 2020 y 2025), así que el split temporal es indispensable y
   los resultados de validación aleatoria serían optimistas.
3. **El estado "Modificado" tiene una tasa de 69 %** y depende del desenlace: filtrar la muestra por estado sesga los
   datos. Recomendación: definir la muestra por fecha de firma.
4. **Dominio de Bogotá** (44 % de los contratos) y de unas pocas entidades: el modelo puede reducirse a "qué entidad firma".
   Evaluar con entidades no vistas o reportar métricas excluyendo las 10 mayores.
5. **14 contratos con `dias_adicionados` > 5 años** (errores de digitación) y valores de contrato extremos
   (hasta 2·10¹⁴): requieren recorte o transformación logarítmica.

## Limitaciones
- Muestra de Salud, no de obra (ver contexto).
- Sin ofertas, garantías ni proveedores todavía (tablas aparte, pendientes de descargar).
- "Adición" es un conteo/indicador: no se conoce el monto adicionado.
- Los contratos de 2025 pueden no haber tenido tiempo de recibir adiciones.
