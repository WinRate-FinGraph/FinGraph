# TrustLens / FinGraph: Start Here

Use these files in this order:

1. [System overview](SYSTEM_OVERVIEW.md) — understand the whole product in five minutes.
2. [Presentation cheat sheet](PRESENTATION_CHEAT_SHEET.md) — explain it in English without overclaiming.
3. [Demo runbook](DEMO_RUNBOOK.md) — run a safe, repeatable demonstration.
4. [Judge Q&A](JUDGE_QA.md) — answer likely technical and business questions.

For deeper study, continue with [the deep documentation index](../deep/README.md).

## The one sentence to remember

FinGraph is a decision-support web application for Indonesian MSME merchants: it verifies a simulated QRIS provider callback, combines deterministic fraud rules with transaction-history and graph signals, then tells the merchant whether to release, verify, or hold an order.

## The most important honesty rule

The current MVP is not connected to Bank Indonesia, a bank, or a real payment service provider. On `GNN-implementation`, QRIS GraphSAGE inference defaults on when an active artifact exists; missing models still fall back to the legacy ensemble. Its available benchmark is synthetic and does not prove accuracy on real QRIS payments. FedAvg remains a demonstrable prototype.
