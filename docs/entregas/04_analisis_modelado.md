# Entrega 4: Diseño del análisis y estrategia de modelado

## 1. Problema que se busca resolver

El proyecto construirá un prototipo para un club de pádel simulado. Estimará la probabilidad de ocupación de cada pista y turno futuro y mostrará una sugerencia de tarifa dentro de límites definidos para la simulación.

El usuario principal será el gestor del club. El resultado le permitirá detectar horas valle, revisar una propuesta de tarifa y decidir si la aplica. La primera versión trabajará con un horizonte de 48 horas antes del inicio del turno. Este horizonte se podrá cambiar cuando se conozca cómo trabaja el club.

El proyecto será útil si mejora una referencia histórica sencilla y si sus probabilidades son fiables. Por ejemplo, entre los turnos a los que se asigne una probabilidad cercana al 70 %, debería acabar ocupado aproximadamente el 70 %.

El objetivo de precios dinámicos se mantendrá. La simulación incluirá distintos precios y una respuesta de la ocupación al precio. Esa respuesta será un supuesto documentado y se probará en varios escenarios; no será una conclusión sobre clientes reales.

## 2. Análisis de datos y utilidad esperada

| Pregunta | Análisis | Utilidad |
| --- | --- | --- |
| ¿Cuándo se ocupan más las pistas? | Ocupación por día de la semana, franja horaria, mes y festivos. | Identificar horas punta y horas valle. |
| ¿Hay diferencias entre pistas? | Comparar ocupación por pista y por tipo de pista. | Ver si una pista exterior o interior tiene un comportamiento distinto. |
| ¿Qué efecto parece tener el clima? | Comparar ocupación con lluvia, viento y temperatura, separando interior y exterior. | Decidir si el clima aporta información al modelo. |
| ¿Qué ocurre con las cancelaciones y bloqueos? | Recuento y evolución de reservas, cancelaciones, no presentados y cierres. | Construir una variable de ocupación correcta. |
| ¿Cómo responde la ocupación al precio en cada escenario? | Comparar ocupación e ingresos simulados por precio, pista y turno. | Comprobar cómo se comporta la regla de precios bajo los supuestos elegidos. |
| ¿Dónde falla el modelo? | Revisar errores por mes, franja, pista y tipo de pista. | Saber cuándo la recomendación necesita más cautela. |

El dashboard mostrará una tabla de ocupación prevista por turno, una matriz histórica por día y franja, la evolución de la ocupación y los principales indicadores: turnos ofertados, ocupados, porcentaje de ocupación e ingresos observados.

## 3. Modelos que se van a plantear

La tarea principal será una **clasificación binaria**: estimar si un turno acabará ocupado (`ocupado_final = 1`) o libre (`ocupado_final = 0`). El modelo devolverá una probabilidad, no solo una respuesta de sí o no.

| Alternativa | Por qué se plantea | Principal límite |
| --- | --- | --- |
| Baseline: media histórica de ocupación por día, franja y tipo de pista. | Es fácil de entender y permite comprobar si el modelo aporta valor. | No usa clima ni relaciones más complejas. |
| Regresión logística. | Es sencilla, rápida y permite explicar qué variables se relacionan con la ocupación. | Puede no recoger relaciones complejas. |
| Modelo de árboles potenciados. | Puede detectar relaciones no lineales entre calendario, clima y tipo de pista. | Requiere más ajuste y es menos fácil de explicar. |

La recomendación de precio inicial será una regla de negocio, no un modelo que afirme conocer el precio óptimo. Por ejemplo, si la probabilidad de ocupación es baja, el sistema puede sugerir una rebaja pequeña; si es alta, mantener la tarifa o sugerir un ajuste limitado. Los límites y los umbrales se definirán en cada escenario.

La simulación probará tres escenarios de respuesta al precio: baja, media y alta. El informe mostrará cómo cambian los resultados entre ellos. Así se evita presentar un único supuesto de demanda como si fuera una medida real.

## 4. Datos de entrada del análisis y los modelos

La fuente principal será `data/gold/gold_slots_pistas.parquet`. Cada fila representará una pista ofertada en un turno del club simulado. La clave será `id_slot` y la fecha principal `fecha_hora_inicio`.

La predicción se generará 48 horas antes del turno. Por ello, las variables de entrada deben existir antes de ese momento.

| Dato | Uso y disponibilidad |
| --- | --- |
| Tipo de pista, día, mes, franja y festivo | Conocidos antes del turno. Se usarán como entradas principales. |
| Ocupación histórica de la misma franja | Se calculará solo con turnos que ya hayan terminado. |
| Tarifa publicada | Se genera para cada turno siguiendo la regla y el escenario de precio activos. |
| Pronóstico meteorológico | Se generará a partir de la meteorología pública con un error controlado y conocido antes del turno. |
| Precio cobrado, ingresos finales y estado final de la reserva | Se usarán para revisar resultados, pero no para predecir ese mismo turno. |
| Clima medido después del turno | Sirve para análisis histórico; no para una predicción anterior. |

Los turnos bloqueados por mantenimiento, torneo u otra causa no se tratarán como turnos libres. Se excluirán del entrenamiento y se mostrarán por separado.

## 5. Datos de salida y forma de consumo

El proceso generará `data/gold/predicciones_turnos.parquet` y el dashboard lo mostrará al gestor. Cada fila será una pista y turno elegible.

| Campo de salida | Significado | Uso |
| --- | --- | --- |
| `id_slot`, `id_pista`, `fecha_hora_inicio` | Identifican el turno. | Localizar el resultado en el calendario. |
| `prob_ocupacion` | Probabilidad de que el turno acabe ocupado. | Detectar riesgo de baja ocupación. |
| `tarifa_vigente` | Precio que figura para el turno. | Punto de partida de la decisión. |
| `tarifa_sugerida` | Precio propuesto dentro de los límites del escenario. | Simulación de una decisión del gestor. |
| `motivo_sugerencia` | Resumen del contexto: franja valle, festivo, pronóstico disponible, etc. | Ayudar a entender la propuesta. |
| `fecha_ejecucion` y `version_modelo` | Cuándo y con qué versión se creó el resultado. | Seguimiento y repetición del proceso. |

Como regla inicial, el sistema podrá sugerir una rebaja máxima del 10 % para turnos con probabilidad baja, mantener el precio con probabilidad media y sugerir un aumento máximo del 10 % cuando la probabilidad sea alta. Estos valores serán parámetros configurables del escenario. Ninguna sugerencia cambiará una reserva ya confirmada.

## 6. Estrategia para diseñar y seleccionar el modelo

1. Generar 24 meses de datos, comprobar el número de turnos, cancelaciones, bloqueos, precios y calidad de las fechas.
2. Crear la variable `ocupado_final` y documentar cómo se tratan cancelaciones y no presentados.
3. Crear las variables de calendario, clima disponible e histórico de ocupación sin usar información futura.
4. Construir el baseline histórico.
5. Entrenar la regresión logística y, si el volumen de datos lo permite, el modelo de árboles.
6. Comparar los modelos en el mismo periodo de validación.
7. Elegir el modelo que combine mejor calidad, estabilidad, facilidad de explicación y coste de mantenimiento.

El modelo de árboles se elegirá solo si mejora de forma clara y estable a la regresión logística. Si la diferencia es pequeña, se utilizará el modelo más sencillo.

## 7. Validación y evaluación

Los datos se dividirán por fecha. No se mezclarán al azar turnos del pasado y del futuro, porque el uso real siempre consiste en predecir fechas posteriores con datos anteriores.

Si hay al menos 12 meses de datos, se usará una separación inicial de 8 meses para entrenamiento, 2 meses para validación y 2 meses finales para prueba. Dentro del periodo anterior a la prueba se harán varios cortes temporales: entrenar con los meses iniciales y validar en meses posteriores. Si hay más historial, se reservarán al menos los últimos 3 meses para prueba.

| Elemento | Decisión |
| --- | --- |
| Métrica principal | **Brier score**: mide si las probabilidades son correctas; cuanto más bajo, mejor. |
| Métricas de apoyo | Gráfico de calibración, ROC-AUC cuando haya suficientes casos de ambos tipos y error de ocupación por día y franja. |
| Comparación | Comparar todas las métricas con el baseline histórico. |
| Criterio de aceptación | El modelo debe tener un Brier score inferior al baseline tanto en validación como en prueba, sin fallos importantes y repetidos en segmentos con suficientes datos. |
| Revisión de errores | Analizar meses, franjas, pistas, tipo de pista, festivos y situaciones de lluvia. |

El periodo de prueba se utilizará al final, una vez elegido el modelo. Si ningún modelo supera al baseline, el dashboard mostrará los análisis descriptivos y el baseline como referencia. La evaluación demostrará el rendimiento dentro del escenario sintético, sin trasladar esa conclusión a un club real.

## 8. Riesgos y alternativas

| Riesgo | Respuesta prevista |
| --- | --- |
| Supuestos poco realistas | Revisar cada regla y comparar los resultados de varios escenarios. |
| El modelo aprende reglas demasiado simples | Usar un baseline y cambiar los parámetros del escenario de prueba. |
| Precio y ocupación demasiado ligados en el generador | Ajustar la elasticidad y mostrar sensibilidad baja, media y alta. |
| Datos sintéticos | Declarar la procedencia y limitar las conclusiones a la simulación. |
| Cambios de horarios, pistas o tarifas | Aplicar escenarios distintos y revisar el rendimiento por periodo. |

La parte con mayor incertidumbre es definir supuestos de ocupación y respuesta al precio que sean razonables. Por ese motivo, el primer paso de la siguiente fase será diseñar y documentar el generador de datos antes de entrenar modelos.
