import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.models.transaction import Transaction


from app.core.config import settings
from app.ml.artifact_security import sign_artifact, verify_artifact

ARTIFACT_DIR = settings.ML_ARTIFACT_DIR
MODEL_PATH = os.path.join(ARTIFACT_DIR, "fraud_baseline_model.pkl")


@dataclass
class MLScoringResult:
    ml_score: float
    ml_risk_level: str
    used_model: bool


def risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def build_features_from_transaction(transaction: Transaction) -> dict[str, Any]:
    return {
        "amount": float(transaction.amount),
        "channel": transaction.channel,
        "source_country": transaction.source_country,
        "destination_country": transaction.destination_country,
        "is_cross_border": int(transaction.source_country != transaction.destination_country),
        "sender_risk_level": transaction.sender_account.risk_level if transaction.sender_account else "low",
        "receiver_risk_level": transaction.receiver_account.risk_level if transaction.receiver_account else "low",
        "device_risk_level": transaction.device.risk_level if transaction.device else "low",
        "device_is_blacklisted": int(transaction.device.is_blacklisted) if transaction.device else 0,
        "merchant_risk_level": transaction.merchant.risk_level if transaction.merchant else "low",
        "merchant_is_blacklisted": int(transaction.merchant.is_blacklisted) if transaction.merchant else 0,
    }


def build_features_from_payload(
    amount: float,
    channel: str,
    source_country: str,
    destination_country: str,
    sender_risk_level: str,
    receiver_risk_level: str,
    device_risk_level: str = "low",
    device_is_blacklisted: bool = False,
    merchant_risk_level: str = "low",
    merchant_is_blacklisted: bool = False,
) -> dict[str, Any]:
    return {
        "amount": float(amount),
        "channel": channel,
        "source_country": source_country,
        "destination_country": destination_country,
        "is_cross_border": int(source_country != destination_country),
        "sender_risk_level": sender_risk_level,
        "receiver_risk_level": receiver_risk_level,
        "device_risk_level": device_risk_level,
        "device_is_blacklisted": int(device_is_blacklisted),
        "merchant_risk_level": merchant_risk_level,
        "merchant_is_blacklisted": int(merchant_is_blacklisted),
    }


class FraudBaselineModel:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
        )
        self.encoders: dict[str, LabelEncoder] = {}
        self.feature_columns = [
            "amount",
            "channel",
            "source_country",
            "destination_country",
            "is_cross_border",
            "sender_risk_level",
            "receiver_risk_level",
            "device_risk_level",
            "device_is_blacklisted",
            "merchant_risk_level",
            "merchant_is_blacklisted",
        ]
        self.categorical_columns = [
            "channel",
            "source_country",
            "destination_country",
            "sender_risk_level",
            "receiver_risk_level",
            "device_risk_level",
            "merchant_risk_level",
        ]

    def _encode_rows(self, rows: list[dict[str, Any]], fit: bool = False) -> np.ndarray:
        encoded_rows = []

        for row in rows:
            encoded_row = []

            for column in self.feature_columns:
                value = row[column]

                if column in self.categorical_columns:
                    value = str(value)

                    if fit:
                        if column not in self.encoders:
                            self.encoders[column] = LabelEncoder()

                    encoder = self.encoders[column]

                    if fit:
                        # Fit later in batch mode, placeholder here.
                        encoded_row.append(value)
                    else:
                        if value not in encoder.classes_:
                            value = encoder.classes_[0]
                        encoded_row.append(int(encoder.transform([value])[0]))
                else:
                    encoded_row.append(float(value))

            encoded_rows.append(encoded_row)

        if fit:
            encoded_array = np.array(encoded_rows, dtype=object)

            for column in self.categorical_columns:
                column_index = self.feature_columns.index(column)
                values = encoded_array[:, column_index].astype(str)
                self.encoders[column].fit(values)
                encoded_array[:, column_index] = self.encoders[column].transform(values)

            return encoded_array.astype(float)

        return np.array(encoded_rows, dtype=float)

    def train(self, transactions: list[Transaction]) -> dict[str, Any]:
        if len(transactions) < 10:
            raise ValueError("Need at least 10 transactions to train baseline model.")

        rows = [build_features_from_transaction(transaction) for transaction in transactions]

        y = np.array([1 if transaction.fraud_score >= 0.55 else 0 for transaction in transactions])

        if len(set(y.tolist())) < 2:
            raise ValueError("Training data must contain both fraud and legitimate samples.")

        x = self._encode_rows(rows, fit=True)

        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=42,
            stratify=y,
        )

        self.model.fit(x_train, y_train)

        y_pred = self.model.predict(x_test)
        accuracy = accuracy_score(y_test, y_pred)

        os.makedirs(ARTIFACT_DIR, exist_ok=True)

        with open(MODEL_PATH, "wb") as file:
            pickle.dump(
                {
                    "model": self.model,
                    "encoders": self.encoders,
                    "feature_columns": self.feature_columns,
                    "categorical_columns": self.categorical_columns,
                },
                file,
            )
        sign_artifact(Path(MODEL_PATH))

        return {
            "message": "Baseline model trained successfully",
            "transactions_used": len(transactions),
            "accuracy": round(float(accuracy), 4),
            "classification_report": classification_report(
                y_test,
                y_pred,
                output_dict=True,
                zero_division=0,
            ),
            "model_path": MODEL_PATH,
        }

    @staticmethod
    def load():
        if not os.path.exists(MODEL_PATH):
            return None

        verify_artifact(Path(MODEL_PATH))
        with open(MODEL_PATH, "rb") as file:
            artifact = pickle.load(file)

        baseline = FraudBaselineModel()
        baseline.model = artifact["model"]
        baseline.encoders = artifact["encoders"]
        baseline.feature_columns = artifact["feature_columns"]
        baseline.categorical_columns = artifact["categorical_columns"]

        return baseline

    def predict_score(self, row: dict[str, Any]) -> MLScoringResult:
        x = self._encode_rows([row], fit=False)

        if hasattr(self.model, "predict_proba"):
            probability = float(self.model.predict_proba(x)[0][1])
        else:
            probability = float(self.model.predict(x)[0])

        return MLScoringResult(
            ml_score=round(probability, 2),
            ml_risk_level=risk_level_from_score(probability),
            used_model=True,
        )


def get_model_status() -> dict[str, Any]:
    exists = os.path.exists(MODEL_PATH)

    return {
        "model_available": exists,
        "model_path": MODEL_PATH if exists else None,
    }


def score_with_baseline_model(row: dict[str, Any]) -> MLScoringResult:
    model = FraudBaselineModel.load()

    if model is None:
        return MLScoringResult(
            ml_score=0.0,
            ml_risk_level="unknown",
            used_model=False,
        )

    return model.predict_score(row)
