# Presentation Cheat Sheet

## 30-second answer

“TrustLens, implemented here as FinGraph QRIS, helps MSME merchants decide whether a digital payment is safe before releasing goods. It verifies a simulated payment-provider callback, checks hard signals such as missing confirmation or amount mismatch, adds behavioral and relationship-based risk, and returns a score and practical action. This demo branch uses GraphSAGE when an active model is available; its evaluation data is synthetic, and FedAvg remains a collaboration prototype.”

## 90-second pitch

“Indonesia's MSMEs increasingly depend on QRIS and other digital payments, but many still verify transactions manually. Fraud is not always visible from one transaction: several accounts can reuse one device, one payer can touch many merchants, or funds can move across regions.

TrustLens treats fraud detection as a decision-support problem. A merchant records the expected order amount. A simulated payment provider sends a signed callback. The backend verifies the callback, builds transaction and relationship features, and combines deterministic rules, the legacy ensemble, and GraphSAGE. When active, GraphSAGE contributes half of the base score. The merchant sees the risk, reasons, and whether to approve, verify, hold, or report.

The current MVP is honest about its maturity. The full merchant workflow, role separation, audit trail, alerts, reporting, and graph exploration work today. The QRIS provider and training benchmark are simulated. GraphSAGE is used when an active artifact is available, but synthetic metrics are not proof of real-world accuracy; FedAvg remains a prototype showing how institutions could collaborate without exchanging raw transaction rows.”

## Five-minute technical structure

1. **Problem:** screenshots and single-transaction rules miss modern fraud patterns.
2. **Input:** order amount, signed provider callback, pseudonymous payer, location, outlet, QRIS profile, and history.
3. **Trust boundary:** HMAC signature, timestamp tolerance, idempotency, ownership, and profile matching.
4. **Decision engine:** GraphSAGE contributes 50% of the base score when active; the legacy ensemble provides the other half and critical rules impose minimum scores.
5. **Output:** risk, confidence, human-readable reasons, alert, and order state.
6. **Learning loop:** merchant/analyst labels become data for optional adaptive retraining.
7. **Architecture:** Next.js, FastAPI, PostgreSQL, optional Neo4j, optional QRIS GraphSAGE, Docker, and Nginx.
8. **Maturity:** working MVP with default-on GraphSAGE when a model exists; synthetic evaluation only, not a deployed banking product.

## Whiteboard version

Draw five boxes:

```text
Order + PJP callback
        |
Security checks
        |
Rules / ML / graph
        |
Score + explanation
        |
Approve / verify / hold / report
```

Add PostgreSQL under all boxes as source of truth. Add Neo4j beside scoring with a dotted line and label it “optional.” Add “feedback labels” looping from the final box back to training.

## Terms worth knowing

- **Fraud score:** normalized risk indicator from `0` to `1`; not proof of guilt.
- **Confidence score:** agreement between available signals; not a calibrated probability of fraud.
- **Graph:** entities plus relationships, useful when individual events look normal but their connections do not.
- **GraphSAGE:** a GNN that aggregates neighboring node information to build node representations.
- **FedAvg:** sample-weighted averaging of model parameters from participating nodes.
- **Pseudonymization:** replacing a payer identifier with a stable keyed-HMAC token. It reduces exposure but is not the same as anonymization.
- **Idempotency:** sending the same callback twice has the same effect as sending it once.
- **False positive:** legitimate payment incorrectly flagged as suspicious.

## Safe claims

- “The MVP performs near-real-time scoring after a simulated callback.”
- “PostgreSQL is the source of truth; Neo4j is optional.”
- “Critical deterministic evidence cannot be suppressed by a low ML score.”
- “The graph explorer uses pseudonymous payer IDs.”
- “FedAvg is a transparent internal simulator.”
- “QRIS GraphSAGE has a canonical adapter, temporal-first training, signed artifacts, and bounded inference with a legacy fallback.”
- “The synthetic benchmark is reproducible, scenario-labelled, and calibrated from adjacent datasets without reusing their identities or claiming their labels are QRIS truth.”

## Claims to avoid

- Do not say the system is connected to Bank Indonesia, banks, or a real PJP.
- Do not say the GNN is validated on production QRIS data.
- Do not say Flower, MLflow, Kubernetes, MinIO, Prometheus, or Grafana are implemented.
- Do not call the confidence score “model accuracy.”
- Do not claim the demo metrics prove production fraud reduction.
- Do not claim pseudonymization makes data anonymous.

## If challenged on the gap between proposal and code

“The proposal states the target architecture. For the hackathon we prioritized an end-to-end, testable merchant decision flow, and added a feature-flagged QRIS GraphSAGE path. The heuristic remains the safe fallback while representative data and validation are still being prepared.”
