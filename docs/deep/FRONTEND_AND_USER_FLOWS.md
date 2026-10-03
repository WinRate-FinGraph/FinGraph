# Frontend and User Flows

## Frontend architecture

The frontend uses Next.js App Router with React client components for authenticated dashboards. `apiFetch()` sends requests to same-origin `/api/v1` by default, adds the stored bearer token, parses JSON errors, and clears cached authentication on `401`.

The dashboard layout:

1. checks browser token;
2. calls `/auth/me` for authoritative current user data;
3. caches refreshed user metadata;
4. applies role and subscription route gating;
5. selects merchant or analyst/admin shell;
6. renders page content inside subscription and outlet providers.

This client gating is not relied upon for backend authorization.

## Public flow

The landing page explains the merchant problem and displays anonymous aggregate metrics from `/public/trust-summary`. Metrics update periodically and are labeled as demo data when applicable. Login and merchant registration lead into the product.

Current asset issue to verify before presentation: `AppLogo` uses `/globe.svg`, while a unit test expects `/logo-mark.png` and `public/logo.svg` references that missing bitmap. The supplied archive does not include `logo-mark.png`. Confirm the intended official identity before changing code or tests.

## Merchant flow

### Home

Merchant home fetches `/merchants/dashboard` with period, selected outlet, and—on Growth/Premium—priority. It emphasizes actions instead of model internals:

- funds received;
- successful payment count;
- payments needing review;
- payments recommended for hold;
- latest payments and alerts;
- quick actions for payment check, order creation, and QRIS profile.

### Create order

The Orders page lists server-paginated orders and lets the merchant record an expected amount for an owned outlet. This expected amount becomes the reference used by amount-mismatch rules.

### Check payment

The payment-check page queries provider reference, amount, and optional order reference. If no payment is found, the API deliberately returns a high-risk “do not release goods” decision instead of a transport-level error. This supports the merchant's practical question: “Should I hand over the product?”

### Payment detail

Detail view presents:

- provider/payment state;
- amount and order context;
- risk and operational recommendation;
- risk score and confidence;
- ensemble or fallback mode;
- reasons and graph context;
- alert and feedback actions.

Presentation helpers enforce safe language: low risk becomes “verified,” medium becomes “needs review,” and unsafe provider states cannot render as approval.

### Alerts

Merchant can view and begin handling its own alerts but cannot resolve/dismiss them or assign an analyst. Hold/report feedback can hold the linked order.

### Reports and plans

Growth adds detailed reporting, category/priority filters, CSV, and action log. Premium is positioned for advanced multi-outlet/investigation capabilities. Demo plan changes do not process money and are recorded as such.

## Analyst flow

Analyst home and navigation focus on investigation:

- global payment list and details;
- merchant list;
- graph intelligence;
- cross-region/cross-border aggregation;
- model artifact and fallback status;
- adaptive-learning readiness;
- federated status;
- audit log.

Analysts can assign and resolve cases and rescore payments. They cannot run admin-only model training, federated rounds, risk configuration, or activity monitoring.

## Admin flow

Admin receives a distinct governance home and analyst access plus:

- activity monitoring;
- risk configuration UI;
- demo scenario laboratory when demo build is active;
- model training actions;
- federated node/round mutations.

Activity Monitoring polls every 30 seconds and can filter by period and role. Data comes from database activity/audit records, not hardcoded cards.

## Graph visualization

The graph page fetches up to 60 nodes by default and caps rendering at 80. It prioritizes high-risk nodes, supports risk/entity/search filters, uses Cytoscape with CoSE-Bilkent layout, and lets the user inspect selected node metadata.

API edge lists are closed over returned nodes, so the renderer does not receive dangling references after truncation.

## Cross-region view

The page shows summary and route tables. Route state is `normal`, `monitor`, or `high` based on score and high-risk proportion. Labels deliberately avoid treating foreign or out-of-region origin as automatic fraud.

## Model and adaptive views

The Model page shows whether GraphSAGE is actually scoring, its share of the final score, the active version, and the legacy fallback. Admin can start training with standard settings or open advanced tuning, watch persisted progress, compare train/validation/test metrics with a feature-only baseline, and review candidates. The first model auto-promotes only when test PR-AUC is defined and at least the baseline; later candidates require explicit promotion. Payment checks and details show the per-payment GNN score and contribution. The Adaptive page shows label counts, class distribution, readiness, and training action.

If no artifact exists, UI explicitly says scoring continues with rule guard and graph heuristic.

## Federated view

The Federated page shows registered nodes, last round, sample totals, before/after demo metric, and privacy statement. Admin can run another round. It must be presented as a simulator.

## Route matrix

| Area | Merchant | Analyst | Admin |
|---|---:|---:|---:|
| Own payments/orders/alerts | Yes | Global view | Global view |
| Merchant reports | Growth+ | No merchant shell | No merchant shell |
| Graph/cross-region | No | Yes | Yes |
| Model/adaptive status | No | Yes | Yes |
| Model training | No | No | Yes |
| Federated status | No | Yes | Yes |
| Run federated round | No | No | Yes |
| Activity monitoring | No | No | Yes |
| Demo Lab | No | No | Demo admin only |

## Frontend test intent

Unit tests verify:

- Indonesian risk/status labels;
- recommendation consistency;
- Jakarta date handling;
- unsafe provider status cannot appear safe;
- role and plan route gating;
- three distinct dashboard homes;
- public metrics are API-driven;
- payment detail exposes score, confidence, mode, and reasons.

Playwright configuration also exists for visual remediation checks, but successful historical results in `RELEASE_READINESS.md` should be rerun on the current machine before being claimed.
