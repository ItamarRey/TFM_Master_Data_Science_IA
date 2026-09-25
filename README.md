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
[ data/raw/ ] ──────────────► Almacenamiento en bruto e inmutable.
   │
   ▼ (Data Pipelines / Cleaning)
[ data/processed/ ] ────────► Datos tipados, limpios y filtrados (Parquet).
   │
   ▼ (Feature Engineering & Joins)
[ data/gold/ ] ─────────────► Datasets analíticos unificados para ML y Dashboard.
```

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

- `data/raw/weather_hourly.json`;
- `data/processed/weather_hourly.parquet`;
- `data/gold/gold_slots_pistas.parquet`;
- `data/gold/gold_slots_pistas_metadata.json`.

Para desarrollar sin conexión se puede usar `python scripts/generate_synthetic_data.py --weather-source synthetic`. Este modo se identifica como sintético en los metadatos y no sustituye la ejecución final con meteorología pública.

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