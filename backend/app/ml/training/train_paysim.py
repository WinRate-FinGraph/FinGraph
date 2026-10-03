from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from app.ml.registry.model_registry import save_model_artifact


ROOT_DIR = Path(__file__).resolve().parents[3]
PAYSIM_PATH = ROOT_DIR / "data" / "raw" / "paysim" / "PS_20174392719_1491204439457_log.csv"


def load_paysim_dataset(limit_rows: int | None = None) -> pd.DataFrame:
    if not PAYSIM_PATH.exists():
        raise FileNotFoundError(
            f"PaySim dataset not found at {PAYSIM_PATH}. "
            "Put the Kaggle CSV file in backend/data/raw/paysim/."
        )

    if limit_rows:
        return pd.read_csv(PAYSIM_PATH, nrows=limit_rows)

    return pd.read_csv(PAYSIM_PATH)


def build_paysim_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    required_columns = {
        "step",
        "type",
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "newbalanceOrig",
        "nameDest",
        "oldbalanceDest",
        "newbalanceDest",
        "isFraud",
        "isFlaggedFraud",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing PaySim columns: {sorted(missing)}")

    data = df.copy()

    data["origin_balance_delta"] = data["oldbalanceOrg"] - data["newbalanceOrig"]
    data["dest_balance_delta"] = data["newbalanceDest"] - data["oldbalanceDest"]
    data["amount_to_old_origin_balance_ratio"] = data["amount"] / (
        data["oldbalanceOrg"].replace(0, np.nan)
    )
    data["amount_to_old_dest_balance_ratio"] = data["amount"] / (
        data["oldbalanceDest"].replace(0, np.nan)
    )

    data["amount_to_old_origin_balance_ratio"] = (
        data["amount_to_old_origin_balance_ratio"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    data["amount_to_old_dest_balance_ratio"] = (
        data["amount_to_old_dest_balance_ratio"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    data["origin_is_customer"] = data["nameOrig"].astype(str).str.startswith("C").astype(int)
    data["dest_is_customer"] = data["nameDest"].astype(str).str.startswith("C").astype(int)
    data["dest_is_merchant"] = data["nameDest"].astype(str).str.startswith("M").astype(int)

    feature_columns = [
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFlaggedFraud",
        "origin_balance_delta",
        "dest_balance_delta",
        "amount_to_old_origin_balance_ratio",
        "amount_to_old_dest_balance_ratio",
        "origin_is_customer",
        "dest_is_customer",
        "dest_is_merchant",
    ]

    x = data[feature_columns]
    y = data["isFraud"].astype(int)

    return x, y


def build_preprocessor() -> ColumnTransformer:
    categorical_features = ["type"]

    numeric_features = [
        "step",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFlaggedFraud",
        "origin_balance_delta",
        "dest_balance_delta",
        "amount_to_old_origin_balance_ratio",
        "amount_to_old_dest_balance_ratio",
        "origin_is_customer",
        "dest_is_customer",
        "dest_is_merchant",
    ]

    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numeric", StandardScaler(), numeric_features),
        ]
    )


def evaluate_model(
    classifier: Any,
    preprocessor: ColumnTransformer,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
) -> dict[str, Any]:
    x_test_processed = preprocessor.transform(x_test)
    probabilities = classifier.predict_proba(x_test_processed)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()

    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    roc_auc = roc_auc_score(y_test, probabilities)
    pr_auc = average_precision_score(y_test, probabilities)

    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0
    false_negative_rate = fn / (fn + tp) if (fn + tp) else 0

    return {
        "threshold": threshold,
        "roc_auc": round(float(roc_auc), 6),
        "pr_auc": round(float(pr_auc), 6),
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(f1), 6),
        "false_positive_rate": round(float(false_positive_rate), 6),
        "false_negative_rate": round(float(false_negative_rate), 6),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "classification_report": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
    }


def train_paysim_xgboost(limit_rows: int | None = None) -> dict[str, Any]:
    df = load_paysim_dataset(limit_rows=limit_rows)

    x, y = build_paysim_features(df)

    fraud_count = int(y.sum())
    legitimate_count = int((y == 0).sum())

    if fraud_count == 0:
        raise ValueError("Dataset contains no fraud samples.")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scale_pos_weight = max(1.0, legitimate_count / fraud_count)

    preprocessor = build_preprocessor()
    x_train_processed = preprocessor.fit_transform(x_train)

    classifier = XGBClassifier(
        n_estimators=250,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
    )

    classifier.fit(x_train_processed, y_train)

    metrics = evaluate_model(
        classifier=classifier,
        preprocessor=preprocessor,
        x_test=x_test,
        y_test=y_test,
    )

    metrics.update(
        {
            "dataset_rows": int(len(df)),
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "fraud_count": fraud_count,
            "legitimate_count": legitimate_count,
            "fraud_ratio": round(float(fraud_count / len(df)), 8),
            "features": list(x.columns),
            "model_family": "xgboost",
        }
    )

    return save_model_artifact(
        model=classifier,
        preprocessor=preprocessor,
        metrics=metrics,
        dataset_name="paysim",
        model_name="xgboost",
    )

def train_paysim_logistic(limit_rows: int | None = None) -> dict[str, Any]:
    df = load_paysim_dataset(limit_rows=limit_rows)
    x, y = build_paysim_features(df)

    fraud_count = int(y.sum())
    legitimate_count = int((y == 0).sum())

    if fraud_count == 0:
        raise ValueError("Dataset contains no fraud samples.")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    preprocessor = build_preprocessor()
    x_train_processed = preprocessor.fit_transform(x_train)

    classifier = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        n_jobs=-1,
    )

    classifier.fit(x_train_processed, y_train)

    metrics = evaluate_model(
        classifier=classifier,
        preprocessor=preprocessor,
        x_test=x_test,
        y_test=y_test,
    )

    metrics.update(
        {
            "dataset_rows": int(len(df)),
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "fraud_count": fraud_count,
            "legitimate_count": legitimate_count,
            "fraud_ratio": round(float(fraud_count / len(df)), 8),
            "features": list(x.columns),
            "model_family": "logistic_regression",
        }
    )

    return save_model_artifact(
        model=classifier,
        preprocessor=preprocessor,
        metrics=metrics,
        dataset_name="paysim",
        model_name="logistic_regression",
    )

if __name__ == "__main__":
    result = train_paysim_xgboost(limit_rows=None)
    print(result)