"""Entrenamiento y comparación reproducible de modelos de ocupación."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from padel_pricing.modeling.dataset import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    split_features_target,
)


BASELINE_SEGMENT = ["franja_horaria", "es_fin_de_semana", "tipo_pista"]


@dataclass
class ExperimentResult:
    """Modelos ajustados, métricas de test y predicciones para auditoría."""

    models: dict[str, Pipeline]
    metrics: dict[str, dict[str, float]]
    test_predictions: pd.DataFrame


def run_experiment(
    train_data: pd.DataFrame, test_data: pd.DataFrame, seed: int
) -> ExperimentResult:
    """Compara baseline histórico, logística y boosting sobre un test posterior."""
    x_train, y_train = split_features_target(train_data)
    x_test, y_test = split_features_target(test_data)
    predictions: dict[str, np.ndarray] = {
        "baseline_historico": historical_baseline_probabilities(train_data, test_data)
    }
    models = {
        "regresion_logistica": build_logistic_model(),
        "gradient_boosting": build_gradient_boosting_model(seed),
    }
    for name, model in models.items():
        model.fit(x_train, y_train)
        predictions[name] = model.predict_proba(x_test)[:, 1]

    metrics = {name: evaluate_probabilities(y_test, values) for name, values in predictions.items()}
    audit = test_data[["fecha_hora_inicio", TARGET_COLUMN]].copy()
    for name, values in predictions.items():
        audit[f"probabilidad_{name}"] = values
    return ExperimentResult(models=models, metrics=metrics, test_predictions=audit)


def historical_baseline_probabilities(
    train_data: pd.DataFrame, test_data: pd.DataFrame
) -> np.ndarray:
    """Estima ocupación por segmento usando únicamente el histórico de entrenamiento."""
    global_rate = float(train_data[TARGET_COLUMN].mean())
    grouped = (
        train_data.groupby(BASELINE_SEGMENT, dropna=False)[TARGET_COLUMN]
        .mean()
        .rename("probability")
        .reset_index()
    )
    joined = test_data[BASELINE_SEGMENT].merge(grouped, on=BASELINE_SEGMENT, how="left")
    return joined["probability"].fillna(global_rate).to_numpy(dtype=float)


def build_logistic_model() -> Pipeline:
    """Modelo lineal explicable con codificación y escalado reproducibles."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                Pipeline(
                    [("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
                ),
                NUMERIC_FEATURES,
            ),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("classifier", LogisticRegression(max_iter=1_000, random_state=42)),
        ]
    )


def build_gradient_boosting_model(seed: int) -> Pipeline:
    """Modelo no lineal para capturar interacciones de calendario, clima y pista."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
        ],
        sparse_threshold=0,
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    learning_rate=0.07,
                    l2_regularization=0.5,
                    max_iter=250,
                    min_samples_leaf=30,
                    random_state=seed,
                ),
            ),
        ]
    )


def evaluate_probabilities(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    """Métricas para una clasificación probabilística, no solo de aciertos."""
    values = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    predicted_class = (values >= 0.5).astype(int)
    return {
        "roc_auc": round(float(roc_auc_score(y_true, values)), 4),
        "average_precision": round(float(average_precision_score(y_true, values)), 4),
        "brier_score": round(float(brier_score_loss(y_true, values)), 4),
        "log_loss": round(float(log_loss(y_true, values)), 4),
        "accuracy_at_0_5": round(float(accuracy_score(y_true, predicted_class)), 4),
        "precision_at_0_5": round(
            float(precision_score(y_true, predicted_class, zero_division=0)), 4
        ),
        "recall_at_0_5": round(float(recall_score(y_true, predicted_class, zero_division=0)), 4),
        "f1_at_0_5": round(float(f1_score(y_true, predicted_class, zero_division=0)), 4),
    }


def select_deployable_model(metrics: dict[str, dict[str, float]]) -> str:
    """Elige entre los modelos predictivos el mejor calibrado según Brier."""
    candidate_names = ["regresion_logistica", "gradient_boosting"]
    return min(candidate_names, key=lambda name: metrics[name]["brier_score"])


def experiment_metadata(result: ExperimentResult, test_start: pd.Timestamp) -> dict[str, Any]:
    """Devuelve metadatos serializables para el artefacto del modelo."""
    return {
        "target": TARGET_COLUMN,
        "features": MODEL_FEATURES,
        "test_start": test_start.isoformat(),
        "selection_metric": "brier_score",
        "metrics": result.metrics,
        "selected_model": select_deployable_model(result.metrics),
    }
