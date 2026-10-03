from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.nn import functional as F

from app.ml.registry.model_registry import save_model_artifact


ROOT_DIR = Path(__file__).resolve().parents[3]
ELLIPTIC_DIR = ROOT_DIR / "data" / "raw" / "elliptic"

CLASSES_PATH = ELLIPTIC_DIR / "elliptic_txs_classes.csv"
EDGES_PATH = ELLIPTIC_DIR / "elliptic_txs_edgelist.csv"
FEATURES_PATH = ELLIPTIC_DIR / "elliptic_txs_features.csv"


class GraphSageLayer(nn.Module):
    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.linear_self = nn.Linear(input_dim, output_dim)
        self.linear_neigh = nn.Linear(input_dim, output_dim)

    def forward(self, x: torch.Tensor, adjacency: list[list[int]]) -> torch.Tensor:
        device = x.device
        neighbor_embeddings = []

        for neighbors in adjacency:
            if neighbors:
                neighbor_idx = torch.tensor(neighbors, dtype=torch.long, device=device)
                neighbor_embeddings.append(x[neighbor_idx].mean(dim=0))
            else:
                neighbor_embeddings.append(torch.zeros(x.shape[1], device=device))

        neigh = torch.stack(neighbor_embeddings, dim=0)

        return self.linear_self(x) + self.linear_neigh(neigh)


class GraphSageClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, dropout: float = 0.25):
        super().__init__()
        self.layer1 = GraphSageLayer(input_dim, hidden_dim)
        self.layer2 = GraphSageLayer(hidden_dim, hidden_dim)
        self.classifier = nn.Linear(hidden_dim, 2)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, adjacency: list[list[int]]) -> torch.Tensor:
        x = self.layer1(x, adjacency)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)

        x = self.layer2(x, adjacency)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)

        return self.classifier(x)


def _validate_files() -> None:
    missing = [
        str(path)
        for path in [CLASSES_PATH, EDGES_PATH, FEATURES_PATH]
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing Elliptic dataset files:\n"
            + "\n".join(missing)
            + "\nPut Kaggle Elliptic CSV files in backend/data/raw/elliptic/."
        )


def load_elliptic_dataset(limit_nodes: int | None = None):
    _validate_files()

    classes = pd.read_csv(CLASSES_PATH)
    edges = pd.read_csv(EDGES_PATH)
    features = pd.read_csv(FEATURES_PATH, header=None)

    # Official Elliptic features format:
    # col 0 = txId, col 1 = timestep, remaining = features.
    feature_columns = ["txId", "time_step"] + [
        f"feature_{i}" for i in range(features.shape[1] - 2)
    ]
    features.columns = feature_columns

    data = features.merge(classes, on="txId", how="left")

    # Keep labelled nodes only for supervision, but graph may include all nodes.
    # class: 1 = illicit, 2 = licit, unknown = unknown.
    data["class"] = data["class"].astype(str)

    if limit_nodes:
        data = data.head(limit_nodes).copy()

    tx_ids = data["txId"].astype(str).tolist()
    id_to_index = {tx_id: idx for idx, tx_id in enumerate(tx_ids)}

    feature_cols = [col for col in data.columns if col.startswith("feature_")]
    x_np = data[feature_cols].astype(float).to_numpy()

    scaler = StandardScaler()
    x_np = scaler.fit_transform(x_np)

    labels = np.full(len(data), -1, dtype=np.int64)

    illicit_mask = data["class"] == "1"
    licit_mask = data["class"] == "2"

    labels[licit_mask.to_numpy()] = 0
    labels[illicit_mask.to_numpy()] = 1

    adjacency: list[list[int]] = [[] for _ in range(len(data))]

    for row in edges.itertuples(index=False):
        source = str(row.txId1)
        target = str(row.txId2)

        if source not in id_to_index or target not in id_to_index:
            continue

        source_idx = id_to_index[source]
        target_idx = id_to_index[target]

        adjacency[source_idx].append(target_idx)
        adjacency[target_idx].append(source_idx)

    return {
        "x": torch.tensor(x_np, dtype=torch.float32),
        "labels": torch.tensor(labels, dtype=torch.long),
        "adjacency": adjacency,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "node_count": len(data),
        "edge_count": int(sum(len(neigh) for neigh in adjacency) / 2),
        "labelled_count": int((labels != -1).sum()),
        "illicit_count": int((labels == 1).sum()),
        "licit_count": int((labels == 0).sum()),
    }


def build_splits(labels: torch.Tensor, train_ratio: float = 0.7, val_ratio: float = 0.15):
    labelled_indices = torch.where(labels != -1)[0]
    y = labels[labelled_indices]

    illicit_indices = labelled_indices[y == 1]
    licit_indices = labelled_indices[y == 0]

    generator = torch.Generator().manual_seed(42)

    illicit_indices = illicit_indices[torch.randperm(len(illicit_indices), generator=generator)]
    licit_indices = licit_indices[torch.randperm(len(licit_indices), generator=generator)]

    def split_class(indices: torch.Tensor):
        n = len(indices)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return indices[:train_end], indices[train_end:val_end], indices[val_end:]

    train_i, val_i, test_i = split_class(illicit_indices)
    train_l, val_l, test_l = split_class(licit_indices)

    train_idx = torch.cat([train_i, train_l])
    val_idx = torch.cat([val_i, val_l])
    test_idx = torch.cat([test_i, test_l])

    train_idx = train_idx[torch.randperm(len(train_idx), generator=generator)]
    val_idx = val_idx[torch.randperm(len(val_idx), generator=generator)]
    test_idx = test_idx[torch.randperm(len(test_idx), generator=generator)]

    return train_idx, val_idx, test_idx


def evaluate_model(
    model: GraphSageClassifier,
    x: torch.Tensor,
    adjacency: list[list[int]],
    labels: torch.Tensor,
    indices: torch.Tensor,
) -> dict[str, Any]:
    model.eval()

    with torch.no_grad():
        logits = model(x, adjacency)
        probabilities = F.softmax(logits[indices], dim=1)[:, 1].cpu().numpy()
        y_true = labels[indices].cpu().numpy()
        y_pred = (probabilities >= 0.5).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    return {
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 6),
        "pr_auc": round(float(average_precision_score(y_true, probabilities)), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "classification_report": classification_report(
            y_true,
            y_pred,
            output_dict=True,
            zero_division=0,
        ),
    }


def train_elliptic_graphsage(
    limit_nodes: int | None = None,
    epochs: int = 20,
    hidden_dim: int = 64,
    learning_rate: float = 0.003,
) -> dict[str, Any]:
    dataset = load_elliptic_dataset(limit_nodes=limit_nodes)

    x: torch.Tensor = dataset["x"]
    labels: torch.Tensor = dataset["labels"]
    adjacency: list[list[int]] = dataset["adjacency"]

    if dataset["illicit_count"] == 0 or dataset["licit_count"] == 0:
        raise ValueError(
            "Elliptic training requires both licit and illicit labelled samples."
        )

    train_idx, val_idx, test_idx = build_splits(labels)

    model = GraphSageClassifier(
        input_dim=x.shape[1],
        hidden_dim=hidden_dim,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=1e-4,
    )

    illicit_train = int((labels[train_idx] == 1).sum().item())
    licit_train = int((labels[train_idx] == 0).sum().item())

    class_weights = torch.tensor(
        [
            1.0,
            max(1.0, licit_train / max(illicit_train, 1)),
        ],
        dtype=torch.float32,
    )

    best_val_f1 = -1.0
    best_state = None

    for epoch in range(1, epochs + 1):
        model.train()

        optimizer.zero_grad()
        logits = model(x, adjacency)

        loss = F.cross_entropy(
            logits[train_idx],
            labels[train_idx],
            weight=class_weights,
        )

        loss.backward()
        optimizer.step()

        val_metrics = evaluate_model(model, x, adjacency, labels, val_idx)
        val_f1 = val_metrics["f1"]

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {
                key: value.detach().clone()
                for key, value in model.state_dict().items()
            }

        print(
            f"[epoch {epoch:03d}] loss={loss.item():.4f} "
            f"val_f1={val_metrics['f1']:.4f} "
            f"val_pr_auc={val_metrics['pr_auc']:.4f}"
        )

    if best_state:
        model.load_state_dict(best_state)

    test_metrics = evaluate_model(model, x, adjacency, labels, test_idx)

    metrics = {
        **test_metrics,
        "dataset_rows": dataset["node_count"],
        "graph_nodes": dataset["node_count"],
        "graph_edges": dataset["edge_count"],
        "labelled_count": dataset["labelled_count"],
        "fraud_count": dataset["illicit_count"],
        "legitimate_count": dataset["licit_count"],
        "fraud_ratio": round(
            float(dataset["illicit_count"] / max(dataset["labelled_count"], 1)),
            8,
        ),
        "train_rows": int(len(train_idx)),
        "validation_rows": int(len(val_idx)),
        "test_rows": int(len(test_idx)),
        "features": dataset["feature_columns"],
        "model_family": "manual_graphsage_pytorch",
        "hidden_dim": hidden_dim,
        "epochs": epochs,
        "warning": (
            "Elliptic is a crypto transaction graph dataset. "
            "Use this model as graph-learning evidence and architecture prototype, "
            "not as direct bank-transfer production model."
        ),
    }

    artifact_model = {
        "state_dict": model.state_dict(),
        "input_dim": int(x.shape[1]),
        "hidden_dim": hidden_dim,
        "scaler": dataset["scaler"],
        "feature_columns": dataset["feature_columns"],
        "architecture": "GraphSAGE",
    }

    return save_model_artifact(
        model=artifact_model,
        preprocessor=None,
        metrics=metrics,
        dataset_name="elliptic",
        model_name="graphsage",
    )


if __name__ == "__main__":
    result = train_elliptic_graphsage(
        limit_nodes=None,
        epochs=20,
        hidden_dim=64,
    )
    print(result)