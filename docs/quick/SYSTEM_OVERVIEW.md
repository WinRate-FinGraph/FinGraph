# System Overview in Five Minutes

## What problem does it solve?

Small merchants often decide whether to release goods by looking at a screenshot or manually checking a payment. A screenshot can be fake, a payment can have the wrong amount, or a callback can be replayed. FinGraph makes the decision explicit: **do not release goods until the payment is verified and its risk is acceptable**.

The proposal calls the broader idea **TrustLens**. The repository implements its hackathon MVP as **FinGraph QRIS**.

## What happens during one payment?

```text
Merchant creates order
        |
Simulator creates pending payment + signed callback
        |
Backend verifies HMAC, timestamp, ownership, and idempotency
        |
Backend builds behavioral features and relationship signals
        |
Rules + tabular model + graph heuristic + adaptive model
                    \ + GraphSAGE (50% total score when active)
        |
Risk score, confidence, reasons, recommendation
        |
Low risk: order paid
Medium/high risk: order held + alert
        |
Merchant/analyst labels outcome; label can support later retraining
```

## Main components

- **Next.js frontend:** landing page, login, role-specific dashboards, payment checking, alerts, reports, graph visualization, ML status, and demo controls.
- **FastAPI backend:** authentication, ownership checks, payment workflow, scoring, alerts, feedback, reporting, and admin APIs.
- **PostgreSQL:** authoritative data store for users, merchants, orders, payments, alerts, labels, audit logs, and federated-round metadata.
- **Neo4j:** optional graph copy for exploration. Payment processing survives when it is unavailable.
- **ML artifact volume:** stores signed model files. Models are not committed to Git.
- **Nginx:** exposes one origin; `/` goes to Next.js and `/api/` goes to FastAPI.

## Three roles

- **Merchant:** sees only its own orders, payments, alerts, QRIS profiles, reports, and action log.
- **Analyst:** investigates all merchants, payments, graph relationships, cross-region activity, and model state.
- **Admin:** gets analyst abilities plus activity monitoring, risk configuration, demo controls, and federated-round controls.

Frontend menus improve usability, but backend role checks and merchant ownership filters provide the real authorization.

## How scoring works

For the QRIS MVP:

```text
legacy = rule × 0.35
       + tabular × 0.30
       + graph heuristic × 0.25
       + adaptive × 0.10

base = GraphSAGE × 0.50 + legacy × 0.50  (when GNN is active)
final = max(severity floor, base), clamped to 0..1
```

If no active GraphSAGE artifact is available or inference fails, `base = legacy`.
The branch enables GNN inference by default, but a missing model is shown as
fallback rather than being reported as active.

Severity floors prevent an optional ML model from overruling hard evidence:

- medium rule: at least `0.50`
- high rule: at least `0.75`
- critical rule: at least `0.90`

Risk classification:

- low: below `0.40`
- medium: `0.40` to below `0.70`
- high: `0.70` or higher

Typical critical evidence: missing official callback, unsuccessful payment claimed as paid, amount mismatch, reused provider reference, merchant/outlet/QR mismatch, or replayed callback.

## What “graph” means here

Nodes represent payer pseudonyms, payments, merchants, outlets, QRIS profiles, providers, regions, countries, orders, and alerts. Edges represent their relationships.

The legacy graph score uses a heuristic based on payer degree, connected merchants, alerts, known fraud labels, and a suspicious-network demo flag. On `GNN-implementation`, a signed QRIS-specific PyTorch Geometric GraphSAGE artifact contributes half of the final base score. The heuristic remains in the other half's legacy ensemble and as a fallback; the Elliptic pipeline remains separate and is not used for QRIS scoring.

## What “Federated Learning” means here

The MVP simulates FedAvg across registered nodes. Each node contributes four deterministic demo parameters and a sample count. The server computes a sample-weighted average and stores round metadata. No transaction rows are shared.

It proves the aggregation workflow and privacy boundary, but it does not yet train local neural networks, use Flower, secure aggregation, differential privacy, or real bank nodes.

## What is real, simulated, and future work?

**Implemented:** web application, authentication, role isolation, order/payment states, signed callback simulator, explainable scoring, alerts, reports, graph explorer, audit log, synthetic data, Docker deployment, and tests.

**Prototype/experimental:** QRIS GraphSAGE scoring on synthetic benchmark data, tabular/adaptive models, FedAvg simulator, and cross-border analytics over demo data. Default-on does not mean validated on real QRIS transactions.

**Not implemented:** official QRIS/PJP connection, bank data integration, Kubernetes, MinIO, MLflow, Prometheus/Grafana, production microservices, real multi-bank federated training, automated billing, and production compliance controls.

## Repository truth versus proposal vision

The PDF describes the intended long-term platform. The code is an MVP proving the merchant workflow and technical building blocks. Present the PDF as vision and the repository as current evidence. Never say all proposal infrastructure is already deployed.
