# Demo Runbook

## Before the meeting

```bash
cp .env.demo.example .env
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml up -d --build
docker compose --env-file .env --profile demo-seed \
  -f docker-compose.yml -f docker-compose.demo.yml run --rm seed-demo
DEMO_MODE=true ./scripts/smoke-test.sh http://localhost
```

Open `http://localhost`.

Demo accounts:

- Merchant: `merchant@fingraph.id` / `password123`
- Analyst: `analyst@fingraph.id` / `password123`
- Admin: `admin@fingraph.id` / `password123`

These credentials are demo-only.

## Recommended eight-minute demo

### 1. Merchant problem and dashboard — 1 minute

Log in as merchant. Show the action-first dashboard: funds received, successful payments, items needing review, and items recommended for hold.

Say: “The merchant should not interpret a screenshot. The system starts from the expected order and provider confirmation.”

### 2. Normal payment — 90 seconds

Open **Pesanan**, create an order, then generate/process a normal demo payment. Open payment detail.

Point out:

- provider status and callback received;
- expected amount versus paid amount;
- low risk and `APPROVE`;
- score, confidence, analysis mode, and reasons.

### 3. Fraud scenario — 90 seconds

Log in as admin and open **Laboratorium Demo**. Run `amount_mismatch` or `fake_receipt`.

Show:

- critical rule;
- score floor at `0.90` or above;
- high-risk classification;
- “do not release goods” recommendation;
- generated alert and held order.

### 4. Analyst view — 2 minutes

Log in as analyst. Show:

- payment investigation;
- Graph Intelligence relationships;
- Cross-Region view;
- Model page showing artifact/fallback status;
- audit trail.

Say: “Neo4j is optional. The graph screen can fall back to PostgreSQL, so payment operations do not fail with the graph service.”

### 5. Federated prototype and limitations — 1 minute

Log in as admin. Show Federated Learning status and one round.

Say: “This is a FedAvg workflow simulator. It shares parameter arrays and sample counts, not raw rows. Secure aggregation and real local training are future work.”

### 6. Close — 1 minute

“The MVP proves the full decision workflow and its safety boundaries. The next external dependency is an official PJP sandbox or institutional partner, followed by evaluation on representative labeled QRIS data.”

## Best scenarios

- `normal_payment`: valid low-risk reference case.
- `fake_receipt`: no provider callback; strongest merchant story.
- `amount_mismatch`: simple and immediately understandable.
- `duplicate_reference`: demonstrates idempotency/reference defense.
- `merchant_qris_mismatch`: demonstrates profile integrity.
- `cross_region`: proves geography alone does not mean fraud.

Use `cross_border` only after explaining that it is context, not automatic guilt.

## Failure recovery

Check services:

```bash
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml ps
```

Check API:

```bash
curl -fsS http://localhost/api/v1/health/live
curl -fsS http://localhost/api/v1/health/ready
```

Check recent logs:

```bash
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml \
  logs --tail=100 reverse-proxy frontend backend migrate
```

If Neo4j is unavailable, continue the demo. Explain the PostgreSQL graph fallback. If model artifacts are unavailable, continue and show `rule_graph_fallback` mode.

Never run `docker compose down -v`; it deletes database and graph volumes.

## Presenter backup

Keep these open in separate tabs before presenting:

1. merchant dashboard;
2. one known high-risk payment detail;
3. graph explorer;
4. model status;
5. this runbook.

If a live mutation fails, use seeded data and explain the same flow from an existing payment. Do not improvise production claims.
