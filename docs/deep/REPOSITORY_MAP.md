# Repository Map

## Identity

- **Proposal name:** TrustLens.
- **Implemented product name:** FinGraph QRIS.
- **Current maturity:** deployment-ready hackathon MVP with production-like configuration.
- **Primary use case:** help an MSME verify a QRIS payment before releasing an order.
- **Data:** deterministic synthetic demo data unless an operator imports external datasets for training.

## Top-level files

| Path | Purpose |
|---|---|
| `README.md` | Setup, deployment, environment, and project status |
| `docker-compose.yml` | Base six-service stack and persistent volumes |
| `docker-compose.demo.yml` | Enables demo endpoints, docs, seed, and registration |
| `docker-compose.prod.yml` | Disables demo behavior and adds resource limits |
| `Makefile` | Common check, test, build, compose, seed, and smoke commands |
| `.env*.example` | Sanitized runtime templates |
| `scripts/smoke-test.sh` | Same-origin end-to-end deployment checks |
| `deploy/nginx/` | Internal reverse proxy and optional host-Nginx example |
| Original proposal PDF | Omitted from the public submission because it contains contributor contact data |

## Backend

```text
backend/
  app/
    api/          HTTP routes and authorization dependencies
    core/         configuration, JWT, passwords, HMAC, pseudonyms
    db/           SQLAlchemy session, seed, admin bootstrap, Neo4j client
    ml/           training, inference, registry, artifact integrity
    models/       SQLAlchemy database entities
    schemas/      Pydantic request/response validation
    services/     scoring, graph sync, reports, audit, FedAvg
    main.py       FastAPI application and router registration
  alembic/        six schema migrations
  tests/          service, configuration, and end-to-end tests
  Dockerfile      Python 3.11 non-root runtime
```

Important backend entry points:

- `app/main.py`: creates FastAPI, middleware, base health routes, and API routers.
- `app/api/demo_qris.py`: simulated provider payment and webhook lifecycle.
- `app/services/qris_scoring.py`: QRIS rules, features, graph heuristic, ensemble, and recommendation.
- `app/db/seeds/seed.py`: deterministic users, merchants, 60 orders/payments, labels, alerts, settlements, and federated nodes.
- `app/api/deps.py`: JWT authentication, role checks, and merchant scope.
- `app/services/graph_sync.py`: Neo4j copy and graph entity relationships.

## Frontend

```text
frontend/
  src/app/             Next.js App Router pages
  src/components/      layout, product, dashboard, and UI components
  src/hooks/           generic authenticated data hook
  src/lib/             API, auth, access, formatting, plans, presentation
  tests/               presentation and access-control unit tests
  public/              static assets
  package.json         Next.js 16, React 19, Cytoscape, Recharts, Base UI
```

Important frontend files:

- `src/lib/api.ts`: same-origin API client and bearer-token injection.
- `src/lib/auth.ts`: login, browser token/user storage, and logout.
- `src/lib/access.ts`: role and plan route visibility.
- `src/components/layout/product-shells.tsx`: role-specific navigation.
- `src/app/dashboard/page.tsx`: merchant, analyst, and admin home selection.
- `src/app/dashboard/payments/[id]/page.tsx`: complete risk explanation and feedback flow.
- `src/app/dashboard/graph/page.tsx`: Cytoscape relationship explorer.

## Runtime services

```text
Public port
   |
Nginx reverse-proxy
   |-- /      -> Next.js :3000
   `-- /api/  -> FastAPI :8000
                    |-- PostgreSQL :5432
                    |-- Neo4j :7687 (optional)
                    `-- ML artifact volume
```

Compose also defines:

- `migrate`: one-shot Alembic upgrade before backend starts;
- `seed-demo`: explicit, profile-gated demo seed job.

Only the reverse proxy publishes a host port. PostgreSQL, Neo4j, backend, and frontend remain on the internal Docker network.

## Sources of truth

- **PostgreSQL:** users, business records, payment state, risk result, labels, alerts, audit, and federated metadata.
- **Neo4j:** optional derived copy for relationship exploration; never authoritative for payment state.
- **ML artifact volume:** optional signed serialized models and metrics.
- **Browser local storage:** JWT and cached user metadata; not authoritative for authorization.
- **PDF:** product vision and claimed target architecture; not proof of code behavior.

## Two transaction domains

The repository contains two related but distinct domains:

1. **Legacy generic transaction domain:** `Account`, `Device`, `Merchant`, `Transaction`. Analyst/admin only. It supports rule scoring plus PaySim and internal adaptive models.
2. **Current QRIS domain:** `MerchantProfile`, `Outlet`, `QRISProfile`, `Order`, `PaymentEvent`. This powers the merchant product and current demo.

Do not mix their thresholds or claim the legacy `Transaction` route is the merchant QRIS decision path.

## Generated or excluded state

The following do not belong in Git:

- real `.env` files;
- `node_modules`, `.next`, caches, and test output;
- databases and backup dumps;
- external datasets;
- serialized model artifacts and signatures;
- private keys, provider tokens, or Cloudflare tunnel credentials.
