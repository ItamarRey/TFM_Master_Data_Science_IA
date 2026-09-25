# Resultados, decisiones y límites del MVP

## 1. Propósito del documento

Este documento deja trazabilidad de las decisiones técnicas, los resultados y
las limitaciones del MVP de predicción de ocupación y recomendación de tarifas
para clubes de pádel. Complementa las entregas previas del proyecto sin
modificarlas.

El objetivo del MVP es estimar la probabilidad de que un turno termine ocupado
48 horas antes de su inicio y usar esa probabilidad en una regla de precios
limitada. No pretende demostrar el precio óptimo ni el impacto económico real
de un club.

## 2. Datos y reproducibilidad

### 2.1. Alcance de los datos

La parte operativa del proyecto es sintética, porque no se dispone de un
dataset público, histórico y verificable de reservas de pádel con el detalle
necesario. La meteorología histórica procede de la fuente pública configurada
(Open-Meteo) y el calendario se construye con festivos públicos.

La simulación cubre 24 meses (2024 y 2025), seis pistas —cuatro exteriores y
dos interiores— y diez turnos diarios de 90 minutos. Esto produce 43.860
turnos ofertados. No se usan datos personales de clientes.

Todas las salidas dependen de una semilla y de parámetros versionados en
`config/simulation_config.json`. Por tanto, son reproducibles, pero solo son
válidas dentro del escenario simulado.

### 2.2. Pipeline de calidad

El pipeline sigue tres capas:

| Capa | Contenido | Tratamiento |
| --- | --- | --- |
| Raw | Extracto operativo sintético y meteorología | Incluye incidencias controladas para probar la limpieza. |
| Silver | Datos tipados y normalizados | Elimina duplicados, normaliza fechas/precios/categorías e imputa previsiones ausentes. |
| Gold | Dataset analítico final | Se publica solo tras superar las validaciones de calidad. |

Las incidencias de Raw son pequeñas, reproducibles y documentadas. No se
interpretan como errores observados en un club real.

## 3. Análisis exploratorio

Gold superó los controles de calidad: no contiene `id_slot` duplicados ni
turnos bloqueados u ocupados a la vez. Los principales resultados son:

| Indicador | Resultado |
| --- | ---: |
| Turnos ofertados | 43.860 |
| Turnos bloqueados | 453 |
| Ocupación de turnos elegibles | 35,07 % |
| Cancelaciones sobre turnos no bloqueados | 3,04 % |
| Ingresos finales simulados | 195.892,50 € |

Los patrones relevantes para modelado y negocio fueron:

- Tarde y noche alcanzan aproximadamente un 46–47 % de ocupación, frente a
  un 27 % por la mañana y al mediodía.
- Sábado y domingo superan el 40 % de ocupación, por encima de los días
  laborables.
- En pistas exteriores, la ocupación pasa de 37,71 % sin lluvia a 17,11 %
  con lluvia moderada o alta.
- Las pistas interiores tienen una ocupación media menor en este escenario.
  No es una conclusión general: también tienen una tarifa media superior y la
  comparación no controla el resto de variables.

El EDA identifica asociaciones internas del escenario; no demuestra relaciones
causales entre precio y ocupación.

## 4. Diseño del experimento de ocupación

### 4.1. Objetivo y prevención de fuga de información

La variable objetivo es `ocupado_final` (`1` ocupado, `0` libre). Los turnos
bloqueados se excluyen del entrenamiento y de la evaluación.

La predicción se realiza 48 horas antes. Por ello se usan únicamente variables
conocidas en ese momento:

- pista, tipo de pista, día, mes, fin de semana, festivo, franja y hora exacta;
- tarifa publicada;
- previsión de temperatura, precipitación y viento;
- indicadores de previsión imputada;
- interacciones entre climatología prevista y pista exterior.

No se usan cancelaciones, ingresos, estado final de reserva ni meteorología
observada, porque no estarían disponibles al realizar la predicción.

### 4.2. División temporal y modelos comparados

Se entrena con los 21.720 turnos anteriores al 1 de enero de 2025 y se evalúa
con los 21.687 turnos posteriores. Esta división temporal evita que el modelo
aprenda con información futura.

Se comparan tres alternativas:

| Modelo | Función en el experimento |
| --- | --- |
| Baseline histórico | Referencia de ocupación media por franja, fin de semana y tipo de pista. |
| Regresión logística | Modelo probabilístico explicable. Codifica categorías, escala variables numéricas y aplica regularización. |
| Gradient boosting | Alternativa no lineal para captar interacciones más complejas. |

La regularización de la logística se selecciona dentro del periodo de
entrenamiento mediante `TimeSeriesSplit` con tres particiones. El parámetro
seleccionado fue `C = 0,01`, lo que favorece un modelo estable frente al ruido.

## 5. Resultados del modelo

| Modelo | ROC-AUC | AP | Brier | Log loss | Accuracy (0,5) | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline histórico | 0,6278 | 0,4487 | 0,2160 | 0,6222 | 0,6575 | 0,5303 | 0,1161 | 0,1905 |
| Regresión logística | **0,6376** | **0,4660** | **0,2148** | **0,6196** | 0,6600 | 0,5333 | 0,1639 | 0,2508 |
| Gradient boosting | 0,6306 | 0,4546 | 0,2160 | 0,6222 | 0,6564 | 0,5235 | 0,1123 | 0,1849 |

Se selecciona la **regresión logística** porque obtiene el menor Brier score y
mejora al baseline en capacidad de discriminación y calidad de las
probabilidades. La mejora es moderada, no espectacular; es coherente con un
escenario que incluye incertidumbre aleatoria y utiliza pronóstico, no clima
observado.

La accuracy no es la métrica principal: con una ocupación cercana al 35 %,
predecir siempre "libre" obtendría una accuracy cercana al 65 %, pero no
aportaría información útil. El producto necesita probabilidades calibradas,
no decisiones binarias automáticas.

### 5.1. Calibración

| Intervalo de probabilidad | Turnos | Ocupación observada | Probabilidad media | Diferencia absoluta |
| --- | ---: | ---: | ---: | ---: |
| 0,0–0,2 | 150 | 0,1733 | 0,1676 | 0,0057 |
| 0,2–0,4 | 13.918 | 0,2779 | 0,2867 | 0,0087 |
| 0,4–0,6 | 7.523 | 0,4756 | 0,4747 | 0,0009 |
| 0,6–0,8 | 96 | 0,5729 | 0,6114 | 0,0385 |

La calibración es especialmente buena en los intervalos con mayor número de
turnos. El tramo 0,6–0,8 debe interpretarse con cautela por su tamaño reducido.
No se obtuvieron predicciones por encima de 0,8, por lo que el MVP no presenta
las estimaciones como certezas.

## 6. Regla de recomendación de precios

La predicción y el precio se mantienen deliberadamente separados. El modelo
estima la ocupación para la tarifa actual; una regla de negocio compara tarifas
candidatas y usa elasticidades explícitas para proyectar un escenario.

La regla evalúa únicamente −10 %, −5 %, mantener tarifa, +5 % y +10 %, dentro
de un rango configurado de 8 € a 20 €. Además:

- con probabilidad baja (menor de 35 %) solo permite mantener o descontar;
- con probabilidad alta (mayor de 65 %) solo permite mantener o incrementar;
- con demanda intermedia mantiene la tarifa.

Las elasticidades de sensibilidad baja, media y alta son supuestos de
configuración. No se estiman de forma causal a partir de los datos simulados.
La decisión final corresponde al gestor y nunca modifica una reserva existente.

## 7. Resultados de escenarios de precio

La siguiente tabla se calcula sobre los 21.687 turnos del periodo de test. Las
reservas e ingresos son **esperados**, es decir, se obtienen al sumar las
probabilidades y `tarifa × probabilidad`; no son resultados reales.

| Escenario | Tarifas modificadas | Reservas esperadas fijas | Reservas esperadas dinámicas | Ocupación esperada dinámica | Ingreso fijo esperado | Ingreso dinámico esperado | Diferencia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sensibilidad baja | 0 | 7.644,76 | 7.644,76 | 35,25 % | 98.337,17 € | 98.337,17 € | 0,00 € |
| Sensibilidad media | 0 | 7.644,76 | 7.644,76 | 35,25 % | 98.337,17 € | 98.337,17 € | 0,00 € |
| Sensibilidad alta | 12.060 | 7.644,76 | 8.064,71 | 37,19 % | 98.337,17 € | 98.975,89 € | +638,72 € |

Interpretación:

- En sensibilidad baja y media, los descuentos no generan suficientes reservas
  esperadas para compensar la reducción de precio. La regla mantiene la tarifa.
- El modelo produce pocos casos de demanda muy alta, por lo que no se justifican
  incrementos de tarifa con los umbrales configurados.
- En sensibilidad alta, los descuentos en turnos de baja demanda elevan las
  reservas esperadas en aproximadamente 420 y el ingreso esperado en 638,72 €.

Este último resultado es una consecuencia de la elasticidad asumida. No permite
afirmar que un club real obtendría ese incremento.

## 8. Decisiones tomadas

| Decisión | Motivo | Evidencia |
| --- | --- | --- |
| Usar datos operativos sintéticos | No existe un dataset público verificable con el detalle necesario. | Supuestos y semilla documentados en configuración. |
| Mantener capas Raw, Silver y Gold | Separar extracto, limpieza y consumo analítico. | Gold supera controles de duplicados y consistencia. |
| Dividir por tiempo | Evitar aprendizaje con información futura. | Entrenamiento 2024 y test 2025. |
| Elegir regresión logística | Mejor Brier, ROC-AUC, AP y log loss frente a las alternativas. | Tabla de resultados de test. |
| Priorizar Brier score | El producto consume probabilidades, no solo clases. | Tabla de calibración. |
| Separar predicción y precio | No se puede inferir causalmente el efecto del precio con estos datos. | Regla de escenarios explícitos. |
| Limitar cambios a ±10 % | Controlar riesgo y mantener una recomendación prudente. | Configuración de precios. |

## 9. Limitaciones y uso responsable

- Las reservas, precios, cancelaciones, bloqueos y elasticidades son sintéticos.
- Los resultados no representan la operación ni los ingresos de un club real.
- El efecto del precio es un supuesto de escenario, no una estimación causal.
- La recomendación requiere revisión del gestor; no se aplica automáticamente.
- Si se obtuvieran datos reales, habría que reentrenar, recalibrar, validar por
  periodos recientes y revisar posibles cambios de comportamiento.

## 10. Reproducción de resultados

Desde la raíz del repositorio:

```text
python scripts/generate_synthetic_data.py
python scripts/run_eda.py
python scripts/train_occupancy_models.py
python scripts/simulate_pricing_scenarios.py
```

Los informes generados se guardan en `reports/generated/` y el modelo
seleccionado en `models/occupancy_model.joblib`.

## 11. Integración del MVP

La aplicación materializa el flujo analítico en una interfaz para la persona
gestora. Su arquitectura es deliberadamente simple y separa responsabilidades:

```mermaid
flowchart LR
    UI["Streamlit: PádelPulse"] --> API["FastAPI: /api/v1/predictions/"]
    API --> MODEL["Modelo de ocupación"]
    API --> RULE["Regla de precios y escenarios"]
    MODEL --> API
    RULE --> API
```

La pantalla **Predicciones** solicita fecha, pista, hora, tarifa actual y el
pronóstico que estaría disponible 48 horas antes. FastAPI convierte esos datos
en las mismas variables empleadas durante el entrenamiento, carga el artefacto
de regresión logística y devuelve:

- probabilidad estimada de ocupación con la tarifa actual;
- tarifa sugerida, variación porcentual y comparación de candidatas;
- ingreso esperado por turno en cada alternativa;
- explicación de los factores considerados y una advertencia de uso.

Las pantallas **Histórico** y **Escenarios** leen, respectivamente, los
indicadores del EDA y la comparación agregada de precios generados por los
scripts reproducibles. La interfaz etiqueta todos los resultados como
sintéticos y la opción de aplicar tarifa solo registra una acción simulada.
No existe automatización de cambios comerciales ni de reservas.

Para ejecutar el recorrido completo se generan los datos, EDA, modelo y
escenarios en ese orden, y se inician `uvicorn backend.app.main:app --reload`
y `streamlit run frontend/streamlit_app.py` en terminales separadas.
