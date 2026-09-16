# Entrega 3: Diseño del Modelo de Datos y Capa Gold del Proyecto

## 1. Resumen de la Idea y Datos del Proyecto

* **Problema que resuelve:** Los clubes de pádel sufren ineficiencias operativas debido al uso de tarifas fijas. Esto provoca pistas desiertas en horas valle y sobredemanda en horas punta, sin optimizar los ingresos (*Revenue Management*) ni adaptar la oferta a factores condicionantes como la meteorología en instalaciones descubiertas o con microclimas.
* **Solución a construir:** Un sistema analítico y predictivo basado en Machine Learning que predice la demanda y la probabilidad de ocupación por slot horario, recomendando un precio dinámico óptimo para maximizar los ingresos por pista disponible (*RevPAC*). Incluirá un Dashboard interactivo de apoyo a la decisión para el gestor del club.
* **Fuentes de datos principales:**
  1. **Dataset de Reservas e Histórico del Club:** Información transaccional sobre ocupación, horarios, pistas, precios históricos y cancelaciones.
  2. **API de Open-Meteo (Historical & Forecast Weather API):** Información meteorológica histórica y predicciones horarias (temperatura, lluvia, viento, nubosidad) en las coordenadas del club.
  3. **Calendario Laboral y Festivos:** Información sobre días laborables, fines de semana y festivos locales/nacionales.

---

## 2. Tecnología o Formato de Almacenamiento Elegido

Para el desarrollo de este proyecto se ha seleccionado una **combinación de Base de Datos Relacional SQLite y Ficheros en Formato Parquet**:

1. **SQLite (Base de Datos Relacional local):**
   * **Justificación:** SQLite no requiere un servidor externo, se integra de forma nativa con Python (`sqlite3`, `SQLAlchemy`, `pandas`) y permite definir relaciones con claves primarias y foráneas de forma limpia. Es ideal para estructurar la base transaccional del proyecto sin sobrecargar la infraestructura del proyecto académico.

2. **Formato Parquet (para las capas intermedias y Gold):**
   * **Justificación:** Los ficheros `.parquet` son columnares y comprimidos (mediante Snappy), lo que optimiza drásticamente las lecturas/escrituras en Python, preservando los tipos de datos exactos (incluyendo timestamps con zona horaria) sin perder precisión ni sufrir problemas de parseo comunes en CSV.

---

## 3. Estructura de Capas de Datos

El flujo y almacenamiento de datos mantendrá la arquitectura medallón (*Medallion Architecture*) mediante la siguiente estructura dentro de la raíz del proyecto:

```text
data/
├── raw/          # Datos en bruto tal como se reciben de las APIs o exportaciones iniciales.
├── processed/    # Datos limpios, normalizados y unificados por fuente.
└── gold/         # Datasets finales agregados, enriquecidos y estructurados para modelos y Dashboard.
```
### Descripción funcional de las capas:
* **`data/raw/`:** Contendrá extractos sin modificar en JSON (respuestas API Open-Meteo) y CSV/SQLite originales de reservas. No se modifican nunca para garantizar la auditabilidad y reproductibilidad.
* **`data/processed/`:** Contendrá ficheros `.parquet` limpios por dominio (`processed_reservas.parquet`, `processed_clima.parquet`). Incluye parseo de fechas, eliminación de duplicados, tipado estricto y filtrado de registros corruptos.
* **`data/gold/`:** Contendrá los datasets consolidados (`gold_pistas_demanda.parquet` y `gold_fact_reservas.parquet`) listos para el Análisis Exploratorio de Datos (EDA), entrenamiento de modelos predictivos y alimentación del Dashboard final.

---

## 4. Definición de la Capa Gold

La capa **Gold** representará el contrato de datos definitivo del proyecto. Se compondrá de un dataset principal granular a nivel de **Slot-Hora-Pista** y una tabla transaccional agregada.

### Dataset Principal: `gold_pistas_demanda.parquet`

* **Descripción funcional:** Dataset unificado de disponibilidad, ocupación real, condiciones meteorológicas y tarifas aplicadas por cada slot de tiempo y pista del club.
* **Nivel de granularidad:** **Slot-Hora por Pista** (por ejemplo: Pista 1, el 2026-04-10 de 18:00 a 19:30).
* **Número aproximado de registros:** ~21.900 filas por año de operación (6 pistas × 10 slots de 90 min/día × 365 días).
* **Uso posterior:** Entrenamiento de modelos de clasificación/regresión de ocupación, lógica de optimización de precios y motor del Dashboard.

| Dataset Gold | Granularidad | Campos clave | Uso posterior |
| :--- | :--- | :--- | :--- |
| `gold_pistas_demanda.parquet` | Pista / Slot de 90 min | `id_slot`, `fecha_hora_inicio`, `id_pista`, `ocupado` (target), `precio_aplicado`, `temperatura_c`, `precipitacion_mm`, `es_festivo` | EDA, Modelos ML de demanda, Engine de Precios Dinámicos, Dashboard en Streamlit. |
| `gold_metricas_diarias.parquet` | Fecha (Día) | `fecha`, `total_ingresos`, `porcentaje_ocupacion`, `revpac`, `ingresos_estimados_optimos` | Dashboard de BI (KPIs ejecutivos para el gestor del club). |

---

## 5. Relaciones entre Datos

El modelo conceptual del proyecto se estructurará mediante un esquema en estrella (*Star Schema*) dentro de la capa relacional/intermedia, que posteriormente se consolida (*denormaliza*) para generar el dataset de la Capa Gold:

```text
  dim_pistas (1)  ───────< (N)
                               fact_reservas (N) >─────── (1) dim_calendario
  dim_clima (1)   ───────< (N)
```

### Explicación de Relaciones y Cruces:
1. **`fact_reservas` con `dim_pistas`:** Relación **N:1** mediante `id_pista`. Permite categorizar la reserva por características de la pista (cubierta vs. descubierta, tipo de superficie).
2. **`fact_reservas` con `dim_clima`:** Relación **N:1** mediante la clave compuesta `(fecha, hora)`. Permite asociar a cada slot horario el estado del tiempo previsto/real.
3. **`fact_reservas` con `dim_calendario`:** Relación **N:1** mediante la clave `fecha`. Permite enriquecer los slots con festivos, fines de semana y estacionalidad.

### Posibles problemas al cruzar fuentes:
* **Descalce de Granularidad Temporal:** Las reservas operan en franjas de 90 minutos, mientras que las APIs meteorológicas suelen entregar lecturas horarias (60 minutos). Se resolverá mapeando las variables climáticas al bloque de inicio de la partida o promediando el impacto climático dentro de los 90 minutos de juego.
* **Zonas Horarias:** Inconsistencias entre la hora UTC devuelta por APIs externas y la hora local (UTC+0 / UTC+1 en Canarias). Se normalizarán todas las estampas temporales a la zona horaria local (`Atlantic/Canary`).

---

## 6. Diccionario de Datos Inicial

A continuación se detallan las variables principales que compondrán el dataset central de la Capa Gold (`gold_pistas_demanda.parquet`):

| Campo | Descripción | Tipo de dato | Fuente | Obligatorio | Observaciones |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id_slot` | Identificador único del slot | `string` | Generado | Sí | Formato: `YYYYMMDD_HHMM_PISTA` |
| `fecha_hora_inicio` | Estampa temporal de inicio | `datetime64[ns]` | Reservas | Sí | ISO 8601 con zona horaria local |
| `duracion_minutos` | Duración del bloque de juego | `int` | Reservas | Sí | Valor por defecto: `90` |
| `id_pista` | Identificador de la pista | `string` | Reservas | Sí | Clave foránea hacia `dim_pistas` |
| `tipo_pista` | Pista cubierta o descubierta | `category` | `dim_pistas` | Sí | Valores: `['Interior', 'Exterior']` |
| `ocupado` | Indicador de ocupación (Target) | `int` / `bool` | Reservas | Sí | `1` = Ocupada, `0` = Libre |
| `precio_aplicado` | Precio cobrado en el slot (€) | `float` | Reservas | Sí | Tarifa base o histórica |
| `temperatura_c` | Temperatura ambiente en °C | `float` | Open-Meteo | Sí | Medición o previsión en ventana de 90 min |
| `precipitacion_mm` | Lluvia acumulada en el slot (mm) | `float` | Open-Meteo | Sí | Crítico para pistas descubiertas |
| `velocidad_viento` | Ráfagas de viento (km/h) | `float` | Open-Meteo | No | Influye en el juego exterior |
| `dia_semana` | Día de la semana | `int` | Calendario | Sí | `0` = Lunes, `6` = Domingo |
| `es_fin_de_semana` | Indicador de fin de semana | `bool` | Calendario | Sí | `True` / `False` |
| `es_festivo` | Indicador de festivo local/nac. | `bool` | Calendario | Sí | `True` / `False` |
| `franja_horaria` | Bloque del día | `category` | Generado | Sí | `['Mañana', 'Tarde', 'Noche']` |

---

## 7. Problemas de Calidad Esperados

1. **Valores Nulos en Clima:** Posible pérdida de conexión o fallos en las llamadas a la API de Open-Meteo.
2. **Desajustes por Reservas Canceladas:** Cancelaciones de última hora que dejan una pista sin ocupar pero con histórico de cobro/penalización parcial.
3. **Pistas fuera de servicio por mantenimiento:** Días u horas donde una pista está bloqueada por obras o eventos, lo cual no debe interpretarse como "falta de demanda".
4. **Outliers en Precios:** Transacciones con descuentos especiales (bonos, torneos, clases de escuela) que no reflejan la tarifa regular.
5. **Cambios de Horario de Verano/Invierno:** Discrepancias de 1 hora al cruzar la serie temporal de clima UTC con la hora local.

---

## 8. Decisiones de Limpieza y Transformación Previstas

* **Tratamiento de Nulos:** Imputación de valores meteorológicos faltantes mediante interpolación lineal temporal (para intervalos cortos < 3h) o la media de la misma franja horaria del día anterior.
* **Filtrado de Registros Inválidos:** Eliminación de slots donde las pistas hayan estado en mantenimiento o bloqueadas administrativamente.
* **Normalización de Fechas:** Conversión obligatoria de todas las columnas de fecha/hora al estándar UTC antes de realizar cruces, re-convirtiendo posteriormente a la zona horaria `Atlantic/Canary` para la capa Gold.
* **Construcción de Variables Derivadas (*Feature Engineering*):**
  * `antelacion_reserva_dias`: Diferencia en días entre el momento de la reserva y la fecha de juego.
  * `indice_mal_tiempo`: Variable sintética booleana o continua que combina lluvia > 0.5mm o viento > 30 km/h en pistas descubiertas.
  * `ocupacion_historica_franja`: Media móvil de ocupación de las últimas 4 semanas para el mismo día y hora.

---

## 9. Riesgos del Modelo de Datos

* **Parte más clara:** La definición de las dimensiones temporales, la captura del clima vía API y la estructura de la tabla factual a nivel de slot de 90 minutos.
* **Parte con mayor incertidumbre:** La estimación precisa de la **elasticidad-precio de la demanda**. Como los datos históricos contendrán precios fijos o con muy poca variación, estimar cómo reaccionará el usuario ante subidas o bajadas de tarifa requiere asumir hipótesis que deberán validarse con cuidado.
* **Fuente más problemática:** El dataset de reservas si proviene de una fuente simulada o con datos poco homogéneos en formatos de fechas.
* **Plan de Contingencia / Simplificación:** Si la denormalización a nivel de pista genera una matriz demasiado dispersa o compleja, el modelo se simplificará agregando la demanda a nivel de **Club-Slot Horario** (ejemplo: % de ocupación global del club en el slot, de 0 a 100%), reduciendo el volumen de datos manteniendo el valor analítico.