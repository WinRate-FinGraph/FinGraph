# Proposal Versus Implementation Audit

## How to read this audit

The 49-page TrustLens PDF is a vision, problem statement, interview appendix, and target technical approach. The repository is a later FinGraph QRIS implementation. This document prevents proposal language from being mistaken for deployed behavior.

Status meanings:

- **Implemented:** end-to-end code path exists and is testable.
- **Prototype:** executable proof exists, but it is not production-equivalent.
- **Simulated:** UI/data flow exists using generated inputs or actors.
- **Not implemented:** proposal claim has no corresponding repository component.

## Core product claims

| Proposal claim | Repository reality | Status |
|---|---|---|
| Real-time fraud detection | Synchronous scoring after simulated provider callback | Simulated |
| MSME decision support | Merchant order/payment/alert/recommendation workflow | Implemented |
| Fraud score and Low/Medium/High | Explainable `0..1` score and three risk levels | Implemented |
| Early warning and preventive action | Alerts plus approve/verify/hold/do-not-release/report actions | Implemented |
| Network visualization | Cytoscape graph from PostgreSQL with optional Neo4j copy | Implemented |
| Continuous feedback | Labels stored; admin-triggered adaptive prototype | Prototype |
| Investigation report | Payment investigation JSON and impact/report pages | Implemented |

## AI claims

| Proposal claim | Repository reality | Status |
|---|---|---|
| Logistic Regression | Synthetic QRIS logistic pipeline and adaptive logistic pipeline | Prototype |
| XGBoost | PaySim training pipeline; not default QRIS runtime | Prototype |
| Heterogeneous GraphSAGE | QRIS PyTorch Geometric GraphSAGE path with typed graph and homogeneous fallback; legacy Elliptic model remains separate | Experimental, default-on in `GNN-implementation` |
| AI Core Engine combines all models | QRIS score blends active GraphSAGE with the legacy rule/tabular/graph/adaptive ensemble; critical rule floors remain | Partial prototype |
| Model learns from user behavior | Hand-engineered historical features and optional labels | Prototype |
| Reduced false positives | No representative production evaluation proving reduction | Not proven |

## Federated-learning claims

| Proposal claim | Repository reality | Status |
|---|---|---|
| Flower framework | No Flower dependency or client/server process | Not implemented |
| FedAvg | Sample-weighted average over simulated parameter arrays | Prototype |
| Local institutional training | No local training workers | Not implemented |
| No raw data sharing | Simulator stores no raw rows in rounds | Implemented boundary in simulator |
| Secure aggregation | Explicitly absent | Not implemented |
| Differential privacy | Explicitly absent | Not implemented |

## Data and integration claims

| Proposal claim | Repository reality | Status |
|---|---|---|
| Core banking input | No connection | Not implemented |
| Payment gateway/PJP input | Internal signed callback simulator | Simulated |
| Device fingerprint and IP networks | Legacy models have fields; current QRIS path centers payer/payment/location | Partial |
| Third-party blacklist/geolocation APIs | No external API | Not implemented |
| Manual upload | No generic transaction-file upload workflow | Not implemented |
| Real labels | Synthetic seed and user-entered demo feedback | Simulated/prototype |
| Cross-border intelligence | Route/region/country aggregates over payment geography | Implemented analytics with demo data |

## Infrastructure claims

| Proposal claim | Repository reality | Status |
|---|---|---|
| Python/FastAPI | Backend | Implemented |
| PostgreSQL | Source of truth | Implemented |
| Neo4j | Optional derived graph | Implemented |
| PyTorch | GraphSAGE training prototype | Prototype |
| PyTorch Geometric | Dependency used by the QRIS GraphSAGE path | Implemented |
| Scikit-learn | Logistic/random-forest pipelines | Implemented |
| MLflow | No dependency or service | Not implemented |
| Next.js | Frontend | Implemented |
| Cytoscape.js | Graph explorer | Implemented |
| Docker | Complete compose stack | Implemented |
| Kubernetes | No manifests/charts | Not implemented |
| MinIO | No service/dependency | Not implemented |
| Prometheus/Grafana | No service/instrumentation | Not implemented |
| Microservices | Modular monolith backend plus separate frontend/databases | Not implemented as microservices |

## Security and scalability claims

Implemented MVP controls include bcrypt, JWT validation, RBAC, merchant ownership, HMAC callback signatures, replay window, idempotency, masking, pseudonymization, trusted hosts, CORS allowlist, artifact HMAC, audit events, pagination, non-root containers, and internal networking.

Missing production controls include provider mTLS, secret manager/KMS, distributed rate limiting, secure federated aggregation, centralized monitoring, encrypted offsite backup, disaster-recovery drill, penetration test, formal privacy/legal review, and production model governance.

## PDF-specific observations

### Problem evidence

The PDF cites MSME, QRIS, scam-loss, and IASC figures dated through 2026. Treat them as proposal citations. Before a public presentation, independently verify every headline number and its date against the linked primary source. The repository does not validate those claims.

One PDF sentence says Indonesia sees 700–800 fraud cases per day with “4.6 trillion per day” losses. That unit/magnitude is especially likely to attract challenge and should not be repeated without source verification.

### Bank interviews

The appendices include BSI-style desk research and transcripts attributed to Bank Muamalat and Bank Mega Syariah. They support discovery, not endorsement or procurement intent. One respondent misunderstands federated learning and says raw data must be forwarded; do not present that answer as technical validation of federated learning.

### Diagrams

The PDF ERD and architecture diagrams describe an earlier generic system with users, accounts, devices, transactions, settings, graph relations, and cross-border summaries. Current code adds a separate QRIS commerce domain and does not contain every diagrammed entity exactly as drawn.

The proposal architecture image includes Flower, MLflow, MinIO, Kubernetes, Prometheus, and Grafana. None is evidence of current implementation.

### Website screenshots

Pages 41–44 show an earlier dark TrustLens interface: profile, system configuration, transaction list, alerts, graph, cross-border map, labeling, simulation, risk map, and audit log. Current Next.js pages implement similar concepts with a newer FinGraph merchant/analyst/admin information architecture. Present screenshots as design lineage, not necessarily the exact current UI.

### Roadmap

The PDF promises preparation, bank/fintech implementation, advanced GNN, federated/regulator collaboration, and global expansion over five months. No partner contract or completed pilot exists in the repository. Present it as an aspirational roadmap.

## Strong, defensible novelty statement

“The MVP's novelty is the combination of merchant-centered payment verification, deterministic safety floors, explainable relationship risk, and an explicit path to privacy-preserving collaboration. We demonstrate the end-to-end workflow today while keeping GNN and cross-institution training as clearly labeled prototypes.”

## Defensible completion statement

“We completed a working, containerized MVP with three roles, payment/order state controls, signed callback simulation, explainable scoring, alerts, reports, audit, graph exploration, adaptive-model plumbing, and federated aggregation simulation. Real provider and bank integration remains the next validation stage.”

## Questions the team should answer consistently

1. **Why FinGraph versus TrustLens?** TrustLens is proposal identity; FinGraph QRIS is current implementation focused on MSME QRIS safety.
2. **Is it production?** No; deployment-ready MVP, not production financial infrastructure.
3. **Is GNN live?** On `GNN-implementation`, QRIS GraphSAGE inference is enabled by default when an active artifact is available. The benchmark is synthetic, so its metrics are not evidence of real-world QRIS accuracy; missing or failed inference uses the legacy scoring fallback.
4. **Is federated learning live?** FedAvg workflow is simulated; real local training is not.
5. **Is cross-border itself suspicious?** No; it is context and requires other risk evidence.
6. **What is measured?** Software invariants and demo behavior. Real-world detection quality is not yet established.

## Highest-priority next steps

1. Obtain official PJP sandbox access and replace merchant-authenticated demo webhook.
2. Define provider data contract, consent, retention, and incident process.
3. Collect representative, legally usable labeled QRIS/payment data.
4. Run temporal evaluation and calibrate thresholds to operational capacity.
5. Replace graph heuristic or validate it against a QRIS-specific learned graph model.
6. Implement authenticated federated clients and secure aggregation only after a real multi-party use case exists.
7. Complete security, observability, backup, and compliance gates before real money or personal data.
