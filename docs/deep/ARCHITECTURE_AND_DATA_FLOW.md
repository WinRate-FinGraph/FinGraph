# Architecture and Data Flow

## Design principles visible in the code

1. PostgreSQL remains authoritative.
2. Safety-critical evidence uses deterministic rules.
3. Optional ML and Neo4j failures degrade capability instead of stopping payments.
4. Merchant ownership is enforced by backend queries.
5. Raw payer identity is transformed before persistence.
6. Demo-only behavior is explicitly configurable and disabled in production settings.

## Application startup

`backend/app/main.py` loads validated settings, configures request logging, installs trusted-host and CORS middleware, and registers API routers under `/api/v1`.

The demo QRIS router is registered only when both `DEMO_MODE` and `ENABLE_DEMO_ENDPOINTS` are enabled. In production, configuration validation rejects demo mode, public registration, auto-seed, weak secrets, wildcard hosts, and wildcard CORS.

Compose startup order is:

```text
PostgreSQL healthy
      |
Alembic migrate completes
      |
FastAPI backend healthy
      |
Next.js frontend healthy
      |
Nginx reverse proxy starts
```

Neo4j is intentionally not a startup dependency of the backend.

## Authentication lifecycle

1. User submits email and password to `POST /auth/login`.
2. Backend performs bcrypt verification. Unknown users still trigger a dummy bcrypt check to reduce timing-based account enumeration.
3. Backend issues a JWT containing subject, expiry, issued-at, not-before, issuer, audience, and unique token ID.
4. Frontend stores JWT and cached user data in `localStorage`.
5. API client attaches `Authorization: Bearer <token>`.
6. `get_current_user()` verifies JWT claims, loads the current user from PostgreSQL, rejects inactive accounts, and updates `last_activity_at` at most once per minute.

The backend ignores the role claim as an authorization source; it reloads the user and current role from the database.

## Merchant scope

`merchant_scope_id()` returns the authenticated merchant profile ID for merchant users and `None` for analyst/admin users. Resource queries add `merchant_id == scope` when the scope exists.

This pattern appears across payments, orders, alerts, labels, reports, audit logs, cross-border data, and graph exploration. A resource belonging to another merchant normally appears as `404`, reducing identifier probing.

## Complete QRIS payment lifecycle

### 1. Create an order

`POST /orders` accepts outlet, expected amount, currency, description, and optional customer reference.

- Only a merchant can create an order.
- Outlet ownership is checked.
- Customer reference is pseudonymized if supplied.
- Initial state is `awaiting_payment`.
- An audit event is written.

Users cannot manually force `paid` or `held`. `completed` is accepted only after `paid`.

### 2. Generate a simulated payment

`POST /demo/qris/generate-payment`:

- checks merchant ownership of the order;
- enforces subscription transaction limit;
- selects the active QRIS profile for the outlet;
- rejects duplicate provider references;
- pseudonymizes the payer identifier;
- creates a pending `PaymentEvent`;
- constructs a canonical callback body;
- signs it with HMAC-SHA256;
- returns the pending payment, payload, and signature.

At this stage the order is not paid.

### 3. Receive the simulated provider webhook

`POST /demo/qris/webhook` performs checks in this order:

1. provider reference exists;
2. authenticated merchant owns it, if caller is a merchant;
3. HMAC signature matches canonical JSON;
4. timestamp parses and falls within tolerance;
5. duplicate callback is identical and therefore idempotent;
6. required callback fields exist;
7. merchant code, outlet code, NMID, and QR fingerprint match the stored profile.

The callback body itself is not stored. The payment stores operational fields and a SHA-256 hash of canonical payload content.

### 4. Build features and score

`score_payment()` queries payer history, recent velocity, recent failures, labels, merchant average amount, and graph-neighborhood statistics. It evaluates rules, loads optional artifacts, computes the ensemble, sets risk/priority/recommendation fields, and stores a complete explanation JSON.

### 5. Transition order and create alert

- Successful callback + low risk: order becomes `paid`.
- Medium or high risk: order becomes `held`.
- Risk score at or above configured alert threshold: create or update one active alert.
- Audit the webhook result.

### 6. Synchronize graph

After the SQL transaction commits, the backend tries to sync the event to Neo4j. Failure is logged and does not roll back the payment.

### 7. Optional QRIS GNN signal

When enabled, scoring queries a bounded PostgreSQL neighborhood around the payer, merchant, outlet, and QRIS profile. The QRIS graph adapter converts canonical rows into a heterogeneous payment/entity graph, or a homogeneous fallback when typed identifiers are unavailable. A signed GraphSAGE artifact produces a fraud score; that score is blended with the existing graph heuristic. Missing artifacts, PyG failures, or inference errors keep the heuristic path and never block payment processing.

### 8. Feedback and adaptive loop

Merchant or staff can label a payment as fraud, legitimate, or suspicious and choose an operational decision. Feedback can hold an order or move an alert into investigation. Merchant feedback cannot:

- mark an unverified order paid;
- dismiss an alert;
- replace provider confirmation.

Valid fraud and legitimate labels with stored features can later train the QRIS adaptive model.

## Order state invariants

```text
awaiting_payment
  | valid success + low risk
  v
paid -----------------> completed

awaiting_payment
  | medium/high risk or merchant hold/report
  v
held
```

An unsuccessful, missing, or suspicious callback never produces a safe order transition.

## Graph data flow

Neo4j receives only derived/pseudonymous QRIS data:

```text
Payer -MADE-> Payment -TO-> Merchant -HAS-> Outlet -USES-> QRIS
                    |          |
                    |          `-- business metadata
                    |-- VIA -> PJP
                    |-- FROM -> Region / Country
                    `-- FOR -> Order
```

The frontend graph endpoint currently builds its response from PostgreSQL even when Neo4j exists. `/graph/sync` rebuilds Neo4j for demonstration and reports graceful fallback if it fails.

## Cross-region and cross-border flow

The payment stores source and destination city, region, and country plus two booleans:

- cross-region: region differs while country remains the same;
- cross-border: country differs.

Geography adds context but does not automatically cause high risk. Route status becomes high only when average risk or the proportion/count of high-risk payments crosses explicit thresholds.

## Federated prototype flow

1. Admin registers at least two nodes with sample counts.
2. Each demo node creates a deterministic four-value local update based on node name and round number.
3. Server calculates sample-weighted average for every parameter.
4. Round stores participants, counts, global parameters, and before/after demo metric.
5. No transaction rows or payer identifiers enter the aggregation record.

This flow models orchestration and aggregation, not actual local model training.

## Reporting and monitoring

Impact dashboards aggregate in SQL, not from a capped browser list. Filters include time period, outlet, priority, category, payment status, and merchant scope. Detail rows remain paginated.

Admin activity monitoring reads audit events and user activity timestamps. Role distribution uses `actor_role` captured at event time, so later role changes do not rewrite history.
