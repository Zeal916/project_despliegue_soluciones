# Hallazgos del EDA sobre obra (SECOP II, 2019–2025)

Cuaderno: `notebooks/03_eda_obra.ipynb` · Figuras: `reports/figures_obra/` · Datos: `contratos_obra_integrado.csv` (78.824 contratos, SECOP Integrado `rpmr-utcd`, origen SECOP II, tipo Obra)
y `adic_senal_prorroga.csv` (1.631.839 modificaciones cuya descripción menciona "prórroga"), versionados con DVC. Scripts: `src/ingest_obra.py`.

## Por qué esta fuente
La tabla `SECOP II – Contratos Electrónicos` (jbjy-vk9h) quedó truncada en origen (1.000 filas desde el 25-oct-2026). SECOP Integrado reúne los contratos de
SECOP II y su `numero_del_contrato` coincide con el `id_contrato` de la tabla Adiciones. **No trae** `dias_adicionados`, origen de los recursos ni saldos.

## Variable objetivo y su validez
- `y_valor`: el contrato figura en la tabla Adiciones con tipo "Adicion en el valor" (exacta).
- `y_tiempo`: **estimada**: el contrato tiene alguna modificación cuya descripción menciona "prórroga".
- Validación contra los `dias_adicionados` reales de 642.540 contratos de Salud (2019–2025): precisión 0,50, recall 0,62, phi 0,40. La señal sobrestima la tasa
  (28,2 % frente a 22,8 %) y es peor en 2019 (52 % frente a 18,5 %). Usar como aproximación; reemplazar por los días reales si la tabla original se restablece.

## Resultados (obra)
| Revisión | Hallazgo |
|---|---|
| Tasa de adición | 56,9 % (valor 10,8 %, tiempo estimado 52,4 %); estable entre años (48–62 %) |
| Nulos | plazo 11 %; tipo de documento del proveedor 58 % no definido |
| Departamentos | 24–72 % (n ≥ 50); Bogotá 28 % de los contratos, 67 % de adición |
| Modalidad | licitación pública de obra 75 %; menor cuantía 58 %; directa 52 %; mínima cuantía 37 % |
| Valor y plazo | decil 1: 23 % → decil 10: 82 %; Spearman valor 0,38, plazo 0,40 |
| Estacionalidad | tasa 52–60 % por mes; el volumen se concentra en diciembre (15.748 contratos) |
| Entidades | 2.499; las 10 mayores = 24 % de los contratos con adición (INVIAS: 6.068 contratos, 85 %) |
| Tiempo vs valor | P(valor \| tiempo) = 12 %, P(tiempo \| valor) = 58 % |
| Fuga | estado_contrato AUC 0,72 (excluir); entidad 0,78, plazo 0,74, valor 0,72 (legítimas) |

## Implicaciones
Partición temporal por fecha de firma; muestra por año y no por estado; PR-AUC y precisión en k; evaluar con entidades no vistas; la etiqueta de tiempo es ruidosa.
