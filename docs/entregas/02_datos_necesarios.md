# Entrega 2: Selección de Idea de Proyecto y Análisis de Datos Necesarios

## 1. Idea Seleccionada

**Optimización de Precios Dinámicos en Clubes de Pádel**

Muchos centros deportivos y clubes de pádel mantienen tarifas fijas o esquemas rígidos (hora punta / hora valle) independientemente de la demanda real y de variables externas cambiantes. Esto genera ineficiencias claras: pistas infrautilizadas en franjas de baja ocupación y saturación con pérdida de ingresos potenciales en momentos de alta demanda. Este problema afecta directamente a los gestores de los clubes, quienes desaprovechan el margen de optimización de sus ingresos (*Revenue Management*), y a los usuarios, que no se benefician de precios más competitivos en horas de baja afluencia. Resolver este problema mediante análisis predictivo permite balancear la oferta y la demanda, maximizando la rentabilidad del centro.

La solución planteada utiliza un enfoque de Data Science y Machine Learning para predecir la ocupación de las pistas y sugerir ajustes dinámicos de tarifas en tiempo real o en ventanas temporales futuras. Mediante el análisis histórico de reservas combinado con datos meteorológicos locales (clave en zonas con microclimas como las Islas Canarias) y variables temporales (festivos, días de la semana, franjas horarias), se entrenará un modelo predictivo de ocupación y demanda. A partir de estas predicciones, un algoritmo de reglas de precios (*Dynamic Pricing*) calculará el precio óptimo por slot horario para maximizar el *Revenue Per Available Court* (RevPAC).

El Producto Mínimo Viable (MVP) constará de un Dashboard interactivo (desarrollado en Streamlit o Power BI) orientado al gestor del club. Este panel permitirá visualizar las predicciones de ocupación para los próximos días, ver las tarifas óptimas recomendadas por el modelo por pista y hora, consultar métricas clave de rendimiento (estimación de ingresos optimizados vs. ingresos con tarifa plana) y simular el impacto de cambios de precio según condiciones meteorológicas previstas.

---

## 2. Datos Necesarios

### Variables o campos necesarios
* **Datos de reservas (Histórico del club):** ID reserva, fecha, hora inicio, hora fin, ID pista, tipo de pista (cubierta/descubierta), estado de reserva (completada, cancelada, no-show), precio cobrado, ID usuario (anonimizado), antelación de la reserva (días entre reserva y juego).
* **Datos meteorológicos:** Fecha/hora, temperatura, precipitación (mm), velocidad del viento, cobertura de nubes, humedad y estado del cielo (despejado, lluvia, etc.).
* **Variables temporales y calendario:** Día de la semana, es_fin_de_semana (booleano), es_festivo_local/nacional (booleano), mes, franja_horaria.

### Granularidad
La granularidad adecuada es **por slot de pista y hora** (por ejemplo, bloques de 60 o 90 minutos por cada pista individual del club).

### Profundidad histórica
Se requiere un mínimo de **12 a 24 meses** de datos históricos de reservas y clima para capturar correctamente la estacionalidad (verano/invierno, festividades, patrones de uso escolar/laboral).

### Volumen aproximado
Para un club medio de 6 pistas operativo 14 horas al día (~84 slots diarios):
* **Reservas:** ~30.000 a 60.000 registros históricos por año.
* **Clima:** ~8.760 registros por año (granularidad horaria).

### Clasificación de datos
* **Imprescindibles:** Histórico de reservas (fecha, hora, pista, estado) y variables temporales/calendario.
* **Deseables (no obligatorios):** Datos meteorológicos históricos y en tiempo real, antelación de reservas, perfil del usuario (nivel de juego, frecuencia) y precios de la competencia.

---

## 3. Fuentes de Datos Previstas

1. **Datos de Reservas de Pádel:**
   * **Fuente:** Generación de un Dataset Sintético basado en distribuciones reales de ocupación de un club local / Exportación anonimizada de software de gestión de reservas (e.g. Playtomic / Matchi si fuera accesible) o scraping de disponibilidad pública.
   * **Formato:** CSV / JSON.
   * **Estabilidad y mantenimiento:** Alta al ser un dataset controlado para el proyecto académico.
   * **Riesgos:** Falta de variabilidad real si el dataset sintético no refleja fielmente sesgos de comportamiento humano.

2. **Datos Meteorológicos:**
   * **Fuente:** API de Open-Meteo (Historical Weather API y Forecast API) o AEMET OpenData.
   * **Enlace:** `https://open-meteo.com/`
   * **Formato:** API JSON / CSV.
   * **Histórico:** Disponible sin costo para datos históricos horarias.
   * **Estabilidad:** Alta, servicio público y muy estable.
   * **Riesgos:** Rate limits menores en planes gratuitos o discontinuidad puntual de la API.

---

## 4. Consideraciones de Privacidad y Protección de Datos

* **Información Identificable:** No se utilizarán datos personales identificables (PII) como nombres, teléfonos, emails o DNI de los usuarios.
* **Anonimización:** Los ID de usuario se codificarán mediante *hashing* o IDs numéricos aleatorios si se analiza el comportamiento de recurrencia.
* **Uso Seguro:** Los datos procesados no vulneran la RGPD al no contener información sensible ni rastreable a personas físicas.
* **Riesgos Éticos:** Evitar dinámicas de *Surge Pricing* abusivas en horas de alta demanda que puedan perjudicar excesivamente al usuario final; la lógica de precios establecerá topes máximos y mínimos éticos.

---

## 5. Viabilidad Inicial del Proyecto

* **Obtención de Datos:** **Alta viabilidad.** Los datos meteorológicos son completamente abiertos y gratuitos. Para las reservas, la combinación de estructura real con simulación/generación sintética fundamentada garantiza la disponibilidad del dataset sin depender de terceros.
* **Calidad y Granularidad:** La granularidad horaria propuesta permite entrenar modelos de series temporales y clasificación/regresión con excelente resolución.
* **Desarrollo durante el curso:** **Realista.** El alcance está bien acotado hacia un MVP enfocado en un Dashboard con modelo predictivo funcional.
* **Parte más arriesgada:** La calibración de la elasticidad de la demanda respecto al precio (cuánto baja la demanda al subir el precio) si solo se dispone de datos de precios fijos pasados.
* **Plan de Alternativa:** Si la integración con datos de clima complica el modelo o las APIs fallan, el proyecto se centrará en un modelo de series temporales puro basado únicamente en el historial de demanda, estacionalidad y calendario festivo.