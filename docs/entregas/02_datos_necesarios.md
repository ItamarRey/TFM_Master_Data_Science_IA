# Entrega 2: Idea seleccionada y datos necesarios

## 1. Idea seleccionada

### Optimización de precios en clubes de pádel

Muchos clubes de pádel mantienen precios fijos por franja horaria. Esto puede dejar pistas libres en horas de poca actividad y dificultar que el club responda cuando la demanda sube. También pueden influir el día de la semana, los festivos, el tipo de pista y, en Canarias, el tiempo meteorológico.

El proyecto creará un prototipo de sistema de apoyo para el gestor de un club. Su objetivo principal será estimar la probabilidad de que una pista se ocupe en un turno futuro. Con esa información, el sistema mostrará una tarifa recomendada dentro de unos límites definidos para la simulación.

La predicción de ocupación y la decisión de precio se tratarán como dos partes del proyecto:

1. El modelo estimará la ocupación esperada de cada turno.
2. Una regla de negocio propondrá una tarifa según esa estimación, la tarifa base y los límites definidos para cada escenario.

El proyecto se construirá con un historial de reservas y precios sintético. Por ello, las recomendaciones y los ingresos calculados serán simulaciones. El trabajo servirá para evaluar el funcionamiento técnico del sistema y comparar modelos dentro del escenario generado; no demostrará el efecto económico en un club real.

El MVP será un dashboard en Streamlit o Power BI. Permitirá consultar la ocupación esperada, los datos que han influido, la tarifa vigente y la tarifa sugerida por pista y turno.

## 2. Datos necesarios

### 2.1 Datos de reservas y disponibilidad sintéticos

Esta será la fuente principal creada para el proyecto. No basta con generar reservas realizadas: también se deben generar los turnos que habrían quedado libres. Cada turno se identificará por pista, fecha, hora de inicio y duración.

| Campo | Uso |
| --- | --- |
| Identificador de pista y tipo de pista | Distinguir pistas interiores y exteriores. |
| Fecha, hora de inicio y duración | Construir los turnos del club. |
| Estado del turno o de la reserva | Diferenciar ocupado, libre, cancelado y bloqueado por mantenimiento. |
| Fecha y hora de creación de la reserva | Simular qué información estaba disponible antes del turno. |
| Fecha y hora de cancelación, si existe | Generar y tratar cancelaciones de forma coherente. |
| Tarifa publicada y precio finalmente cobrado | Analizar precios y medir ingresos. |
| Fecha de publicación o modificación de la tarifa, si existe | Saber qué precio se conocía antes de hacer la predicción. |
| Motivo de bloqueo, si existe | No confundir una pista cerrada con falta de demanda. |

La primera versión no incluirá datos personales ni perfiles de jugadores. Los identificadores de reserva y pista serán códigos generados para el proyecto.

### 2.2 Datos de calendario

Se utilizarán día de la semana, mes, franja horaria, fin de semana y festivos nacionales, autonómicos o locales. Estos datos ayudan a explicar patrones que se repiten y están disponibles antes del turno.

### 2.3 Datos meteorológicos

Se utilizarán temperaturas, lluvia, viento, humedad y nubosidad de fuentes públicas. A partir de esos datos se generará un pronóstico sintético con un error controlado, disponible 48 horas antes del turno.

La meteorología será especialmente útil para las pistas exteriores. El valor medido se utilizará para describir el histórico y el pronóstico sintético se utilizará como entrada del modelo.

### 2.4 Granularidad y periodo histórico

La unidad de trabajo será una **pista en un turno ofertado**. La simulación utilizará turnos de 90 minutos para mantener una estructura simple y consistente.

Se generarán 24 meses de datos para incluir dos ciclos anuales completos. El calendario y la meteorología se basarán en fuentes públicas reales; las reservas, cancelaciones, precios y bloqueos se generarán mediante reglas documentadas.

La simulación representará un club de seis pistas, cuatro exteriores y dos interiores, con diez turnos diarios de 90 minutos. Esto genera un máximo de 21.900 turnos ofertados por año antes de descontar bloqueos. Estos parámetros estarán centralizados en la configuración para poder cambiarlos.

## 3. Fuentes previstas y forma de obtención

| Fuente | Qué aporta | Viabilidad y condiciones |
| --- | --- | --- |
| Generador de datos del proyecto | Turnos, reservas, cancelaciones, bloqueos, precios y ocupación final. | Fuente principal. Las reglas, parámetros y semilla aleatoria se guardarán para repetir la simulación. |
| Open-Meteo | Datos históricos de temperatura, lluvia y viento para Canarias. | Fuente pública real para dar contexto meteorológico a cada turno. [Documentación](https://open-meteo.com/en/docs). |
| AEMET OpenData | Datos meteorológicos de contraste en España. | Fuente pública complementaria. [Portal](https://opendata.aemet.es/centrodedescargas/inicio). |
| Calendarios oficiales | Festivos nacionales, autonómicos y locales. | Fuente real para las variables de calendario. |

No se ha identificado un conjunto abierto, histórico y verificable de reservas de pádel con el detalle necesario para este proyecto. Por esa razón, las variables operativas se generarán de forma sintética. El método de generación se documentará para que sea posible revisar cada supuesto.

## 4. Privacidad y uso responsable

El dataset sintético no contendrá nombres, teléfonos, correos, documentos ni perfiles de jugadores. Los datos de calendario y meteorología son públicos.

Las recomendaciones de precio tendrán límites mínimo y máximo definidos en la configuración del escenario. No usarán atributos personales de los jugadores ni cambiarán el precio de una reserva ya confirmada.

## 5. Viabilidad inicial y riesgos

El proyecto es viable porque no depende de la entrega de datos por parte de un club. Los datos de calendario y meteorología son accesibles y el resto se generará de manera reproducible.

La simulación incluirá varios niveles de precio por pista, turno y periodo. También incluirá una respuesta de la ocupación al precio que será un supuesto explícito del escenario, no un comportamiento observado en clientes reales. Se probarán al menos tres escenarios: sensibilidad baja, media y alta al precio.

El MVP mostrará predicciones, reglas de tarifa y resultados simulados. Permitirá comprobar si el pipeline de datos, los modelos y el dashboard funcionan correctamente. Las conclusiones se limitarán al escenario sintético y no se presentarán como resultados de un club real.
