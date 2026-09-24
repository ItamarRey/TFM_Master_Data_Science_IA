# Entrega 3: Modelo de datos y capa Gold

## 1. Objetivo de los datos del proyecto

El proyecto combinará datos públicos de calendario y meteorología con datos sintéticos de turnos, reservas, precios, cancelaciones y bloqueos. El objetivo es construir un conjunto de datos que permita responder dos preguntas dentro de un escenario simulado:

1. ¿Qué probabilidad hay de que una pista se ocupe en un turno futuro?
2. ¿Qué tarifa puede proponer el sistema dentro de los límites definidos en cada escenario?

La primera pregunta se resolverá con el histórico sintético de ocupación. La segunda se tratará con reglas de negocio y escenarios de precio. La relación entre precio y demanda será un supuesto documentado de la simulación.

## 2. Almacenamiento elegido

El proyecto utilizará SQLite y archivos Parquet.

- **SQLite** guardará tablas de reservas, pistas, calendario y bloqueos durante la preparación de los datos. Es sencillo de usar desde Python y no necesita un servidor.
- **Parquet** se usará para los datos limpios y para la capa Gold. Conserva bien los tipos de fecha y permite leer solo las columnas necesarias en los análisis y modelos.

## 3. Capas de datos

```text
data/
├── raw/          # Respuestas de APIs, calendarios y datos generados sin transformar.
├── processed/    # Datos limpios y normalizados por fuente.
└── gold/         # Datos finales para análisis, modelos y dashboard.
```

- **raw:** no se modifica. Contiene el resultado original del generador, las respuestas de APIs y los calendarios.
- **processed:** contiene `processed_reservas.parquet`, `processed_turnos.parquet`, `processed_clima.parquet` y `processed_calendario.parquet`.
- **gold:** contiene los datos consolidados que usará el proyecto.

## 4. Capa Gold

### 4.1 Dataset principal: `gold_slots_pistas.parquet`

Este es el dataset principal. Cada fila representa una **pista ofertada en un turno concreto**. Se incluirán tanto los turnos que acabaron ocupados como los que quedaron libres. Los turnos bloqueados por mantenimiento, torneo u otra causa se marcarán para excluirlos del entrenamiento.

La clave será `id_slot`, creada con `id_pista`, fecha, hora de inicio y duración. La fecha de referencia será `fecha_hora_inicio`.

| Campo | Tipo | Descripción y uso |
| --- | --- | --- |
| `id_slot` | texto | Identificador único del turno de pista. |
| `id_pista` | texto | Identificador de la pista. |
| `tipo_pista` | categoría | Interior, exterior u otra clasificación del club. |
| `fecha_hora_inicio` | fecha y hora | Inicio del turno. Se guardará en UTC y se mostrará en horario de Canarias. |
| `duracion_minutos` | entero | Duración real del turno ofertado. |
| `estado_turno` | categoría | Libre, ocupado, cancelado o bloqueado. |
| `ocupado_final` | 0/1 | Variable objetivo: 1 si el turno acabó ocupado y 0 si quedó libre. |
| `precio_publicado` | número | Tarifa generada para el turno según el escenario de precio. |
| `precio_cobrado` | número | Importe final de una reserva. Se usa para ingresos y revisión, no para predecir el mismo turno. |
| `dia_semana`, `mes`, `franja_horaria` | categoría | Variables de calendario. |
| `es_fin_de_semana`, `es_festivo` | 0/1 | Indicadores de calendario. |
| `temperatura_c`, `precipitacion_mm`, `velocidad_viento` | número | Datos meteorológicos públicos usados para describir el histórico. |
| `pronostico_temperatura_c`, `pronostico_precipitacion_mm`, `pronostico_velocidad_viento` | número | Pronóstico sintético disponible antes del turno. |
| `fecha_emision_pronostico` | fecha y hora | Marca que el pronóstico se generó 48 horas antes del turno. |
| `bloqueado` y `motivo_bloqueo` | 0/1 y texto | Evitan tratar cierres como falta de demanda. |
| `origen_dato` | categoría | Indica si el campo procede de una fuente pública o del generador sintético. |

Para una predicción hecha antes del turno solo entrarán al modelo datos disponibles en ese momento. Por ejemplo, el calendario y el historial anterior sí pueden usarse; el precio cobrado al final, una cancelación posterior o la lluvia medida después no.

### 4.2 Dataset de indicadores: `gold_metricas_diarias.parquet`

Cada fila representa un día de actividad del club. Se construye a partir de `gold_slots_pistas.parquet` y se utiliza en el dashboard, no para predecir los turnos del mismo día.

| Campo | Descripción |
| --- | --- |
| `fecha` | Día analizado. |
| `turnos_ofertados` | Número de turnos que el club puso a disposición. |
| `turnos_ocupados` | Número de turnos ocupados al cierre. |
| `porcentaje_ocupacion` | Turnos ocupados dividido entre turnos ofertados. |
| `ingresos_simulados` | Suma de los importes simulados cobrados. |
| `revpac_simulado` | Ingresos simulados divididos entre turnos ofertados. |

Los ingresos que resulten de una tarifa sugerida se guardarán aparte para comparar escenarios de simulación.

## 5. Relaciones entre los datos

Durante la preparación se utilizará un modelo con tablas separadas y luego se creará la capa Gold.

```text
dim_pistas       ─┐
dim_calendario   ─┼──> fact_turnos_y_reservas ───> gold_slots_pistas
dim_clima        ─┘
```

- `dim_pistas` describe cada pista: identificador, tipo y otras características estables.
- `dim_calendario` contiene fechas, días de semana y festivos.
- `dim_clima` contiene datos meteorológicos públicos por hora y los pronósticos sintéticos correspondientes.
- `fact_turnos_y_reservas` une el calendario de turnos ofertados con las reservas, cancelaciones y bloqueos.

El calendario de turnos es imprescindible: si se parte solo de las reservas, no se conocen los turnos que quedaron libres.

## 6. Transformaciones previstas

1. Crear el calendario de turnos a partir de la configuración del club simulado: seis pistas, horario y duración de los turnos.
2. Unir reservas, cancelaciones y bloqueos al turno correspondiente.
3. Normalizar fechas y horas. Se guardarán en UTC para los cruces técnicos y se mostrará `Atlantic/Canary` en el dashboard.
4. Limpiar duplicados, duraciones incorrectas, importes imposibles y estados de reserva inconsistentes.
5. Unir calendario y meteorología a cada turno. Si un dato meteorológico falta, se marcará la ausencia y se aplicará una imputación sencilla definida dentro del entrenamiento.
6. Crear variables históricas, como la ocupación media de la misma franja en semanas anteriores. Estas variables solo usarán turnos que ya habían terminado antes de la fecha de predicción.
7. Separar los campos de uso predictivo de los campos que solo sirven para análisis posterior, como los ingresos finales.

## 7. Calidad de datos y controles

| Riesgo | Control previsto |
| --- | --- |
| La simulación genera reservas, pero no turnos libres | Generar primero todos los turnos ofertados y después asignar reservas y bloqueos. |
| Una cancelación se interpreta mal | Definir una regla para cada estado: cancelada, no presentada, confirmada y bloqueada. |
| Horas incorrectas por cambio horario | Guardar el instante en UTC y revisar los cambios de horario de Canarias. |
| Precio sin variación suficiente | Definir varios niveles de tarifa y documentar la elasticidad usada en cada escenario. |
| Pronóstico sintético demasiado exacto | Introducir un error controlado y documentar cómo se genera. |
| Una pista se cierra por mantenimiento | Excluir el turno del entrenamiento y mostrarlo aparte. |

## 8. Alcance y alternativa

El generador creará 24 meses de datos y guardará una semilla aleatoria, los parámetros de ocupación y los escenarios de precio. Esto permitirá repetir exactamente el dataset y variar un supuesto cada vez para estudiar cómo cambia el resultado.

El modelo y la política de precios se validarán dentro de los escenarios generados. El proyecto demostrará la viabilidad técnica del enfoque, pero no permitirá afirmar que las mismas métricas o ingresos se obtendrían en un club real.
