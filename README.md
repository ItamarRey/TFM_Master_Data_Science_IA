# PádelPulse: precios dinámicos para clubes de pádel

Base técnica del MVP del TFM. El proyecto usa datos operativos sintéticos y meteorología pública para estimar la ocupación de un turno y sugerir una tarifa dentro de límites configurados.

La carpeta `docs/` no se incluye a propósito: conserva tus entregas anteriores en el repositorio principal.

## Inicio rápido en Windows con VS Code

Desde la raíz del proyecto, abre una terminal de PowerShell y ejecuta:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

En VS Code selecciona el intérprete de `.venv`. Después, usa dos terminales:

```powershell
uvicorn backend.app.main:app --reload
streamlit run frontend/streamlit_app.py
```

La API quedará disponible en `http://127.0.0.1:8000`, su documentación en `/docs` y el dashboard en `http://localhost:8501`.

## Ejecutar el MVP completo

Antes de abrir una predicción, genera los artefactos que consume la aplicación:

```powershell
python scripts/generate_synthetic_data.py
python scripts/run_eda.py
python scripts/train_occupancy_models.py
python scripts/simulate_pricing_scenarios.py
```

Después inicia la API y Streamlit en dos terminales, desde la raíz del proyecto:

```powershell
uvicorn backend.app.main:app --reload
streamlit run frontend/streamlit_app.py
```

En **Predicciones**, introduce la fecha, pista, tarifa publicada y pronóstico a
48 horas. La interfaz llama a `POST /api/v1/predictions/`, muestra la
probabilidad estimada y compara las tarifas permitidas. La aplicación nunca
modifica reservas ni tarifas reales: la acción de aplicar es una simulación.

## Comprobaciones

```powershell
pytest
ruff check .
ruff format --check .
```

## Análisis exploratorio

Después de generar el dataset Gold, ejecuta:

```powershell
python scripts/run_eda.py
```

El script no modifica los datos. Genera un informe Markdown y un fichero JSON en
`reports/generated/` con controles de calidad, ocupación por franja y pista,
efecto de la lluvia en pistas exteriores e ingresos simulados.

## Estructura

- `frontend/`: interfaz Streamlit y componentes visuales.
- `backend/`: API FastAPI, validación y servicios.
- `src/padel_pricing/`: lógica reutilizable de simulación, modelos y reglas de precio.
- `data/`: datos locales generados; no se suben datos pesados al repositorio.
- `models/`: artefactos del modelo entrenado; no se suben al repositorio.
- `config/`: escenarios y parámetros configurables.

## Orden de implementación

1. Generar los datos sintéticos y guardarlos en `data/gold/`.
2. Crear variables y baseline histórico.
3. Entrenar y evaluar el modelo de ocupación.
4. Implementar la regla de tarifa y los escenarios.
5. Conectar los endpoints de FastAPI.
6. Conectar el dashboard Streamlit con la API.
