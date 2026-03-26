from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.prediction_training.models import (
    PredictionDatasetRun,
    PredictionModelArtifact,
    PredictionModelType,
    PredictionTrainingRun,
    PredictionTrainingStatus,
)
from apps.prediction_training.services.dataset import FEATURE_COLUMNS

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None


MIN_ROWS_FOR_TRAINING = 30


@dataclass
class TrainingResult:
    training_run: PredictionTrainingRun
    model_artifact: PredictionModelArtifact | None


def _artifact_root() -> Path:
    base = Path(settings.BASE_DIR) / 'artifacts' / 'prediction_training'
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_dataset(dataset_run: PredictionDatasetRun):
    rows: list[list[float]] = []
    labels: list[int] = []
    with Path(dataset_run.artifact_path).open('r', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append([float(row[column]) for column in FEATURE_COLUMNS])
            labels.append(int(row['label']))
    import numpy as np

    return np.array(rows, dtype=np.float32), np.array(labels, dtype=np.int32)


def _summarize_metrics(y_true, probabilities) -> dict:
    from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, log_loss

    preds = (probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y_true, preds, labels=[0, 1])
    return {
        'accuracy': round(float(accuracy_score(y_true, preds)), 6),
        'log_loss': round(float(log_loss(y_true, probabilities, labels=[0, 1])), 6),
        'brier_score': round(float(brier_score_loss(y_true, probabilities)), 6),
        'confusion_matrix': matrix.tolist(),
    }


def run_training(*, dataset_run: PredictionDatasetRun, model_name: str = 'xgboost_baseline') -> TrainingResult:
    started_at = timezone.now()
    training_run = PredictionTrainingRun.objects.create(
        status=PredictionTrainingStatus.RUNNING,
        dataset_run=dataset_run,
        model_type=PredictionModelType.XGBOOST,
        started_at=started_at,
    )

    artifact = None

    try:
        import joblib
        import numpy as np
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import train_test_split

        X, y = _load_dataset(dataset_run)
        if len(X) < MIN_ROWS_FOR_TRAINING:
            raise ValueError(f'Not enough rows to train. Need at least {MIN_ROWS_FOR_TRAINING}, got {len(X)}.')
        if XGBClassifier is None:
            raise RuntimeError('xgboost is not installed. Install dependencies before training.')

        X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

        model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=42,
        )
        model.fit(X_train, y_train)

        calibrator = CalibratedClassifierCV(model, cv='prefit', method='sigmoid')
        calibrator.fit(X_valid, y_valid)
        calibrated_probs = calibrator.predict_proba(X_valid)[:, 1]
        metrics = _summarize_metrics(y_valid, calibrated_probs)

        root = _artifact_root()
        model_path = root / f'model_run_{training_run.id}.joblib'
        calibrator_path = root / f'calibrator_run_{training_run.id}.joblib'
        metadata_path = root / f'model_run_{training_run.id}.json'
        joblib.dump(model, model_path)
        joblib.dump(calibrator, calibrator_path)
        metadata_path.write_text(
            json.dumps(
                {
                    'feature_columns': FEATURE_COLUMNS,
                    'label_definition': dataset_run.label_definition,
                    'feature_set_version': dataset_run.feature_set_version,
                },
                indent=2,
            ),
            encoding='utf-8',
        )

        with transaction.atomic():
            training_run.status = PredictionTrainingStatus.SUCCESS
            training_run.finished_at = timezone.now()
            training_run.rows_used = len(X)
            training_run.artifact_created = True
            training_run.validation_summary = metrics
            training_run.summary = 'XGBoost model trained and calibrated with sigmoid.'
            training_run.details = {
                'feature_columns': FEATURE_COLUMNS,
                'split': {'train_rows': int(len(X_train)), 'validation_rows': int(len(X_valid))},
                'calibration_method': 'sigmoid',
            }
            training_run.save()

            artifact = PredictionModelArtifact.objects.create(
                name=model_name,
                version=f'run-{training_run.id}',
                model_type=PredictionModelType.XGBOOST,
                label_definition=dataset_run.label_definition,
                feature_set_version=dataset_run.feature_set_version,
                training_run=training_run,
                validation_metrics=metrics,
                artifact_path=str(model_path),
                calibrator_path=str(calibrator_path),
                metadata={'metadata_path': str(metadata_path), 'feature_columns': FEATURE_COLUMNS},
            )
    except Exception as exc:
        training_run.status = PredictionTrainingStatus.FAILED
        training_run.finished_at = timezone.now()
        training_run.summary = f'Training failed: {exc}'
        training_run.details = {'error': str(exc)}
        training_run.save(update_fields=['status', 'finished_at', 'summary', 'details', 'updated_at'])
        raise

    return TrainingResult(training_run=training_run, model_artifact=artifact)
