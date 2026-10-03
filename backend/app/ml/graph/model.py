from __future__ import annotations

from typing import Any

import torch
from torch import nn


def _pyg():
    try:
        from torch_geometric.nn import HeteroConv, SAGEConv
    except ImportError as exc:
        raise RuntimeError("torch-geometric is required for QRIS GraphSAGE") from exc
    return HeteroConv, SAGEConv


class HeterogeneousGraphSAGE(nn.Module):
    def __init__(self, node_types: list[str], edge_types: list[tuple[str, str, str]], hidden_dim: int = 64, dropout: float = 0.2):
        super().__init__()
        HeteroConv, SAGEConv = _pyg()
        self.model_kind = "heterogeneous_graphsage"
        self.hidden_dim = hidden_dim
        self.dropout = dropout
        self.node_types = node_types
        self.edge_types = edge_types
        self.conv1 = HeteroConv({edge: SAGEConv((-1, -1), hidden_dim) for edge in edge_types}, aggr="mean")
        self.conv2 = HeteroConv({edge: SAGEConv((-1, -1), hidden_dim) for edge in edge_types}, aggr="mean")
        self.classifier = nn.Linear(hidden_dim, 2)

    def forward(self, x_dict: dict[str, torch.Tensor], edge_index_dict: dict[tuple[str, str, str], torch.Tensor]):
        x_dict = self.conv1(x_dict, edge_index_dict)
        x_dict = {key: torch.relu(value) for key, value in x_dict.items()}
        x_dict = {key: torch.dropout(value, self.dropout, self.training) for key, value in x_dict.items()}
        x_dict = self.conv2(x_dict, edge_index_dict)
        return self.classifier(torch.relu(x_dict["payment"]))


class HomogeneousGraphSAGE(nn.Module):
    def __init__(self, edge_types: list[tuple[str, str, str]], hidden_dim: int = 64, dropout: float = 0.2):
        super().__init__()
        _, SAGEConv = _pyg()
        self.model_kind = "homogeneous_graphsage"
        self.hidden_dim = hidden_dim
        self.dropout = dropout
        self.edge_types = edge_types
        self.conv1 = SAGEConv(-1, hidden_dim)
        self.conv2 = SAGEConv(-1, hidden_dim)
        self.classifier = nn.Linear(hidden_dim, 2)

    def forward(self, x_dict: dict[str, torch.Tensor], edge_index_dict: dict[tuple[str, str, str], torch.Tensor]):
        x = x_dict["node"]
        edge_index = torch.cat(list(edge_index_dict.values()), dim=1)
        x = torch.relu(self.conv1(x, edge_index))
        x = torch.dropout(x, self.dropout, self.training)
        return self.classifier(torch.relu(self.conv2(x, edge_index)))


def build_model(snapshot_schema: dict[str, Any], hidden_dim: int = 64, dropout: float = 0.2) -> nn.Module:
    edge_types = [tuple(edge) for edge in snapshot_schema["edge_types"]]
    if snapshot_schema.get("mode") == "homogeneous_fallback":
        return HomogeneousGraphSAGE(edge_types, hidden_dim, dropout)
    return HeterogeneousGraphSAGE(snapshot_schema["node_types"], edge_types, hidden_dim, dropout)
