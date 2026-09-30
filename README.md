# PádelPulse

> MVP de precios dinámicos para clubes de pádel

PádelPulse ayuda a la persona gestora de un club a decidir la tarifa de un turno concreto. Estima la probabilidad de ocupación a partir del calendario, el tipo de pista, la tarifa actual y la previsión meteorológica, y propone una tarifa dentro de límites configurados.

El gestor siempre revisa y decide. La aplicación no modifica reservas, pagos ni tarifas reales.

## Qué incluye

- Predicción de ocupación para un turno concreto.
- Previsión meteorológica automática mediante Open-Meteo.
- Simulación manual de condiciones meteorológicas para pruebas.
- Recomendación de tarifa con variaciones limitadas.
- Histórico de demanda por horario, día, tipo de pista y lluvia.
- Comparación de escenarios de precio.
- Calendario de tarifas simuladas aplicadas por el gestor.

## Alcance del MVP

El proyecto utiliza datos operativos sintéticos y meteorología pública. El escenario cubre 24 meses, seis pistas y 43.860 turnos ofertados.

La regresión logística fue el modelo seleccionado para estimar ocupación. Se evaluó sobre un periodo temporal posterior al entrenamiento y obtuvo un Brier score de 0,2069 y un ROC-AUC de 0,6350.

Estos resultados validan el funcionamiento del MVP dentro del escenario simulado. No prueban un beneficio económico real para un club ni sustituyen una validación con reservas reales.

## Inicio rápido en Windows con VS Code

Desde la raíz del proyecto, abre PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

En VS Code, selecciona el intérprete de `.venv`.

## Generar los artefactos del MVP

En una terminal con el entorno virtual activado:

```powershell
python scripts/generate_synthetic_data.py
python scripts/run_eda.py
python scripts/train_occupancy_models.py
python scripts/simulate_pricing_scenarios.py
```

## Ejecutar la aplicación

Abre dos terminales desde la raíz del proyecto.

Terminal 1:

```powershell
uvicorn backend.app.main:app --reload
```

Terminal 2:

```powershell
streamlit run frontend/streamlit_app.py
```

- Dashboard: `http://localhost:8501`
- API: `http://127.0.0.1:8000`
- Documentación de la API: `http://127.0.0.1:8000/docs`

## Uso del producto

1. En **Predicciones**, selecciona fecha, pista, hora y tarifa vigente.
2. La aplicación consulta automáticamente la previsión meteorológica del turno.
3. Revisa la probabilidad estimada, las tarifas candidatas y la recomendación.
4. Aplica o mantén la tarifa. La decisión se registra solo en el calendario simulado.
5. Consulta **Tarifas**, **Histórico** y **Escenarios** para completar el análisis.

La predicción representa el contexto disponible antes del turno. El efecto de las alternativas de precio se muestra como un escenario basado en elasticidades configuradas, no como una estimación causal demostrada en un club real.

## Comprobaciones

```powershell
pytest
ruff check .
ruff format --check .
```

## Estructura del proyecto

```text
backend/               API FastAPI, validación y servicios
frontend/              Dashboard Streamlit y componentes visuales
src/padel_pricing/     Lógica reutilizable de datos, modelos y precios
scripts/               Generación de datos, EDA, entrenamiento y escenarios
config/                Parámetros de simulación y reglas de precio
data/                  Datos generados localmente
models/                Modelo entrenado generado localmente
reports/generated/     Informes generados por los scripts
docs/                  Entregas y documentación del proyecto
```

## Próximos pasos

Para implantar PádelPulse en un club real sería necesario integrar su sistema de reservas, anonimizar y validar los datos, reentrenar el modelo con su histórico y realizar un piloto controlado frente a tarifas fijas.
