# 🎾 Dynamic Pricing & Demand Forecasting for Padel Clubs

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion%20(Raw--Processed--Gold)-orange.svg)](#arquitectura-de-datos)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Un sistema end-to-end de **Data Science & Machine Learning** diseñado para optimizar el *Revenue Per Available Court (RevPAC)* en centros deportivos mediante estrategias de precios dinámicos. El proyecto aborda la ineficiencia de las tarifas fijas prediciendo la demanda horaria por pista e integrando variables exógenas como microclimas y festividades.

---

## 📋 Tabla de Contenidos
- [Visión General](#vision-general)
- [Arquitectura de Datos](#arquitectura-de-datos)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Capa Gold y Contrato de Datos](#capa-gold-y-contrato-de-datos)
- [Instalación y Configuración](#instalacion-y-configuracion)
- [Roadmap del Proyecto](#roadmap-del-proyecto)

---

## <a name="vision-general"></a>🎯 Visión General

El modelo de negocio de los clubes de pádel tradicionales presenta dos problemas operacionales críticos:
1. **Pistas desiertas en horas valle** debido a barreras de precio fijo.
2. **Saturación en horas punta** sin captura de margen adicional por alta disposición al pago.

Esta solución utiliza modelos predictivos para estimar la probabilidad de ocupación por pista en slots de **90 minutos** y recomendar la tarifa óptima en tiempo real. 

### Principales Variables del Sistema:
* **Histórico Transaccional:** Patrones de reserva por día, hora y tipo de pista (interior/exterior).
* **Meteorología (API Open-Meteo):** Precipitación, viento y temperatura en tiempo real e histórica (clave en instalaciones descubiertas o zonas microclimáticas).
* **Calendario Dinámico:** Festivos locales, días laborables y estacionalidad.

---

## <a name="arquitectura-de-datos"></a>🏛️ Arquitectura de Datos

El pipeline aplica una **Arquitectura Medallón (Medallion Architecture)** combinando **SQLite** para la persistencia relacional transaccional y **Apache Parquet** para almacenamiento columnar comprimido en las capas analíticas:

```text
  [ Fuentes Externas ] 
   │  ├─ API Open-Meteo (JSON)
   │  └─ Reservas Club (SQLite/CSV)
   ▼
[ data/raw/ ] ──────────────► Extractos de origen, sin limpiar.
   │
   ▼ (Data Pipelines / Cleaning)
[ data/processed/ ] ────────► Datos tipados, limpios y filtrados (Parquet).
   │
   ▼ (Feature Engineering & Joins)
[ data/gold/ ] ─────────────► Datasets analíticos unificados para ML y Dashboard.
```

Para validar el pipeline sin datos de un club, la simulación añade en Raw un volumen pequeño y reproducible de duplicados, formatos de fecha/precio/categoría inconsistentes y valores ausentes de pronóstico. Son incidencias de prueba documentadas en configuración; no se interpretan como comportamiento real de un club. Silver las normaliza y Gold solo se publica si cumple el contrato de calidad.

---

## <a name="estructura-del-repositorio"></a>📁 Estructura del Repositorio

```text
├── data/                  # Estructura Medallón (git-ignored en entornos prod)
│   ├── raw/               # Extractos crudos de APIs y fuentes de origen
│   ├── processed/         # Datasets limpios por dominio (.parquet)
│   └── gold/              # Datasets consolidados para modelado y BI (.parquet)
├── docs/                  # Documentación del proyecto y entregables
│   └── entregas/          # Hitos incrementales del curso
│       ├── 01_ideas_producto.md
│       ├── 02_datos_necesarios.md
│       └── 03_modelo_datos.md
├── notebooks/             # Notebooks de EDA y prototipado de modelos
├── src/                   # Código fuente modularizado (Pipelines, ETL, ML)
├── .gitignore             # Filtros de exclusión para datos sensibles y temporales
├── README.md              # Documentación principal del repositorio
└── requirements.txt       # Dependencias del proyecto
```

---

## <a name="capa-gold-y-contrato-de-datos"></a>📊 Capa Gold y Contrato de Datos

El dataset central de trabajo (`gold_pistas_demanda.parquet`) consolida la información a nivel de **Slot de 90 min por Pista**:

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id_slot` | `string` | PK sintética (`YYYYMMDD_HHMM_PISTA`) |
| `fecha_hora_inicio` | `datetime64` | Timestamp ISO 8601 con TZ local |
| `duracion_minutos` | `int` | Bloque base de juego (90 min) |
| `id_pista` | `string` | FK identificador de la pista |
| `tipo_pista` | `category` | Interior / Exterior |
| `ocupado` | `int` / `bool` | Target (`1` = Ocupada, `0` = Libre) |
| `precio_aplicado` | `float` | Tarifa aplicada en € |
| `temperatura_c` | `float` | Temperatura ambiente estimada |
| `precipitacion_mm` | `float` | Precipitación acumulada en el slot |
| `es_festivo` | `bool` | Indicador de festividad |

---

## <a name="instalacion-y-configuracion"></a>⚙️ Instalación y Configuración

### 1. Clonar el repositorio
```text
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

### 2. Crear entorno virtual e instalar dependencias
```text
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

---

## Generar el dataset sintético

El primer dataset se genera desde la raíz del repositorio:

```text
python scripts/generate_synthetic_data.py
```

El comando descarga meteorología histórica pública para la ubicación configurada y crea:

- `data/raw/weather_hourly.json`: extracto horario de meteorología;
- `data/raw/operational_slots_raw.csv`: extracto operativo simulado con incidencias de calidad controladas;
- `data/processed/weather_hourly.parquet`;
- `data/processed/silver_slots_pistas.parquet`: datos operativos limpios y tipados;
- `data/processed/operational_quality_report.json`: incidencias inyectadas y resultado de la limpieza;
- `data/gold/gold_slots_pistas.parquet`;
- `data/gold/gold_slots_pistas_metadata.json`.

Para desarrollar sin conexión se puede usar `python scripts/generate_synthetic_data.py --weather-source synthetic`. Este modo se identifica como sintético en los metadatos y no sustituye la ejecución final con meteorología pública.

Las tasas de incidencia se configuran en `config/simulation_config.json`, dentro de `data_quality`. La semilla hace que tanto la simulación como esas incidencias sean reproducibles. No cambies las tasas después de generar resultados que vayas a comparar en la memoria.

---

## Análisis exploratorio

Después de generar el dataset Gold, ejecuta:

```text
python scripts/run_eda.py
```

El script no modifica los datos y trabaja únicamente sobre Gold. Por ello es correcto que sus controles indiquen cero duplicados: estos deben haberse detectado y resuelto antes, en Silver. Genera `reports/generated/eda_summary.md` y `reports/generated/eda_metrics.json` con controles de calidad, ocupación por franja y pista, efecto de la lluvia en pistas exteriores e ingresos simulados.

---

## Entrenamiento y comparación de modelos

Tras generar Gold, ejecuta:

```text
python scripts/train_occupancy_models.py
```

El experimento excluye turnos bloqueados y usa solo variables disponibles 48 h antes: calendario, hora exacta, pista, tarifa publicada y pronóstico meteorológico. Incluye interacciones entre el pronóstico y las pistas exteriores. Reserva el segundo año como test temporal, por lo que nunca usa datos posteriores para entrenar.

Compara un baseline histórico por segmento, una regresión logística y un modelo de gradient boosting. La regularización de la logística se ajusta con validación temporal interna. El modelo desplegable se selecciona entre los modelos predictivos por menor Brier score, una métrica de calidad de probabilidades. El informe añade una tabla de calibración para comprobar que las probabilidades son coherentes. Genera:

- `models/occupancy_model.joblib`;
- `models/occupancy_model_metadata.json`;
- `reports/generated/model_comparison.md`;
- `reports/generated/occupancy_test_predictions.parquet`.

La comparación mide capacidad predictiva; no identifica de forma causal el efecto del precio ni prueba un impacto económico real. La recomendación de tarifa se tratará después mediante escenarios de sensibilidad explícitos.

---

## Escenarios de precios

Después de entrenar el modelo, ejecuta:

```text
python scripts/simulate_pricing_scenarios.py
```

La regla toma la probabilidad estimada para la tarifa actual y compara únicamente cinco opciones: −10 %, −5 %, mantener, +5 % y +10 %, respetando los límites configurados. Solo contempla descuentos ante demanda baja, aumentos ante demanda alta y mantener el precio ante demanda intermedia.

El efecto de modificar la tarifa se calcula con elasticidades explícitas para sensibilidad baja, media y alta. Genera `reports/generated/pricing_scenarios.md` y `reports/generated/pricing_scenarios.json`, con la comparación entre tarifa fija y dinámica esperada.

El resultado es una simulación de escenarios para apoyar al gestor; no es una estimación causal del precio óptimo ni se aplica automáticamente.

---

## <a name="roadmap-del-proyecto"></a>🚀 Roadmap del Proyecto

- [x] **Fase 1:** Definición del caso de uso e impacto de negocio (`01_ideas_producto.md`)[cite: 2]
- [x] **Fase 2:** Análisis de viabilidad y requerimientos de datos (`02_datos_necesarios.md`)[cite: 2]
- [x] **Fase 3:** Diseño de la arquitectura de datos y Capa Gold (`03_modelo_datos.md`)[cite: 2]
- [ ] **Fase 4:** Pipelines de Extracción y Ingesta ETL (Open-Meteo & Reservas)
- [ ] **Fase 5:** Exploración de Datos (EDA) y Feature Engineering
- [ ] **Fase 6:** Entrenamiento y Evaluación de Modelos ML (Clasificación/Regresión de Demanda)
- [ ] **Fase 7:** Algoritmo de Precios Dinámicos y Despliegue del Dashboard (Streamlit)

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.