# Backend, Data, and Security

## Database domains

### Identity and tenancy

- `users`: login identity, role, active state, login/activity timestamps.
- `merchant_profiles`: one-to-one merchant business profile, subscription, risk, and status.
- `outlets`: merchant-owned locations.
- `qris_profiles`: outlet QRIS metadata, masked settlement account, and payload fingerprint.

### Commerce and payment

- `orders`: expected amount, outlet, description, expiry, and state.
- `payment_events`: provider reference, amount, callback state, geography, scores, explanations, and recommendation.
- `settlements`: demo settlement records for low-risk successful payments.

### Risk operations

- `alerts`: risk case linked to payment or legacy transaction.
- `labels`: feedback/ground truth candidate linked to payment or legacy transaction.
- `audit_logs`: actor snapshot, action, entity, merchant scope, and metadata.

### Collaboration prototype

- `federated_nodes`: demo participant, sample count, and last round.
- `federated_rounds`: participants, weighted parameters, and demo metrics.

### Legacy benchmark domain

- `accounts`, `devices`, `merchants`, `transactions`, and `countries` support older generic transaction and dataset experiments.

## Important constraints and indexes

- Email, merchant code, outlet code, NMID, order reference, transaction reference, provider reference, settlement reference, node name, and round number are unique.
- Merchant, status, risk, priority, and time combinations are indexed for dashboards and investigation.
- Foreign keys connect operational entities, while application checks enforce ownership.
- Alembic migrations are the deployment schema authority; current expected head is `20260723_0006`.

## API groups

| Prefix | Main responsibility |
|---|---|
| `/auth` | register merchant, login, current user |
| `/merchants` | profiles, plans, dashboard, outlets, QRIS profiles |
| `/orders` | create/list/state/match payment |
| `/payments` | list, verify reference, detail, explanation, rescore |
| `/demo/qris` | provider simulator, webhook, scenarios |
| `/alerts` | risk-case workflow |
| `/labels` | feedback and adaptive-learning evidence |
| `/reports` | impact dashboard, CSV, investigation report |
| `/graph` | relationship explorer and Neo4j sync |
| `/cross-border` | geography summaries, routes, regions, timeline |
| `/ml` | model inventory, status, and admin training |
| `/federated` | nodes, rounds, privacy summary |
| `/audit-logs` | scoped action history |
| `/admin` | admin-only activity monitoring |
| `/public` | anonymous aggregate landing-page metrics |
| `/transactions` | analyst/admin legacy generic transaction API |

Exact request/response schemas are available through FastAPI OpenAPI when `ENABLE_API_DOCS=true`.

## Role and plan controls

Backend roles:

- merchant: scoped operational access;
- analyst: global investigation access;
- admin: governance and mutation of privileged controls.

Examples of backend-only restrictions:

- legacy transaction API: analyst/admin;
- model training: admin;
- graph sync: analyst/admin;
- federated node/round mutation: admin;
- activity monitoring: admin;
- public registration: merchant only and disabled in production.

Subscriptions enforce transaction and outlet limits in backend QRIS creation paths. Frontend route gating improves navigation but is not the security boundary.

## Password and JWT security

- Passwords use bcrypt through Passlib.
- Login performs a dummy bcrypt verification for unknown accounts.
- JWT verifies algorithm, signature, expiry, issuer, and audience.
- Token subject must parse as UUID.
- Current user and role are reloaded from PostgreSQL.
- Inactive users are rejected.

Current limitation: browser token is stored in `localStorage`, access tokens default to 24 hours, and no refresh-token rotation/revocation store exists. Production should prefer short-lived access tokens, secure cookie or hardened token storage, refresh rotation, and revocation/session management.

## Provider callback security

The simulator uses:

- canonical JSON with sorted keys and compact separators;
- HMAC-SHA256 signing;
- constant-time signature comparison;
- configurable timestamp tolerance;
- unique provider reference;
- identical-callback idempotency;
- conflict on a different callback for an already processed reference;
- merchant ownership filtering;
- merchant, outlet, NMID, and QR fingerprint matching.

The demo webhook still requires a user JWT. Real provider integration should use a provider-specific trust mechanism such as mTLS, signed provider credentials, source controls, replay storage, and key rotation—not a merchant browser token.

## Privacy boundaries

### Payer

`pseudonymize_payer()` lowercases and trims the raw identifier, then applies HMAC-SHA256 with a private key and stores a 24-hex-character prefix under `payer_...`.

Properties:

- stable for the same normalized identifier and key;
- supports relationship analysis;
- original value is not directly visible;
- resistant to simple rainbow tables when the key remains secret.

Limitations:

- same identifier remains linkable inside the system;
- key compromise permits targeted guessing;
- truncation reduces theoretical collision resistance;
- it is pseudonymous personal data, not anonymous data.

### QRIS and settlement

- settlement account stores only final four characters;
- QR payload stores SHA-256 fingerprint rather than raw content;
- webhook stores operational fields and canonical payload hash rather than full raw payload.

### Federated records

Round metadata records node identity, sample count, and parameters. It declares zero raw rows shared. Parameters themselves can leak information in real federated learning, which is why secure aggregation and privacy analysis remain required.

## ML artifact security

Serialized artifacts are HMAC-signed and path-confined before loading. This is a useful integrity control, but `joblib`/pickle remains code-execution-capable. Only artifacts produced by trusted training code under protected storage should ever be loaded.

## Audit behavior

Important operations create an `AuditLog` with:

- actor email/name;
- actor role snapshot;
- action;
- entity type and ID;
- user and merchant scope;
- description and optional metadata;
- timestamp.

Role snapshot protects historical reporting from later role changes. Audit data is operational evidence, not a tamper-proof ledger. Production needs append-only controls, restricted retention, export/SIEM integration, and monitoring for deletion or modification.

## Availability and graceful degradation

- PostgreSQL unavailable: readiness fails and traffic should stop.
- migration mismatch: readiness fails.
- Neo4j unavailable and optional: readiness is degraded; SQL fallback remains.
- model artifact unavailable: rules and graph heuristic remain.
- demo seed never runs automatically in production.

## Security gaps before real financial use

1. Official provider authentication and contractual data source.
2. TLS termination and managed certificate lifecycle.
3. KMS/secret manager and rotation procedures.
4. Distributed rate limiting and stronger replay/idempotency storage.
5. CSRF/token-storage review and hardened browser security headers/CSP.
6. Dependency, container, SBOM, and secret scanning.
7. Encrypted backups, restore drills, and retention/deletion policies.
8. Central logging, alerting, incident response, and SIEM.
9. Penetration test, threat model, privacy impact assessment, and Indonesian regulatory/legal review.
10. Model governance, drift monitoring, human-appeal path, and adverse-decision policy.

## Seed data

The idempotent seed creates:

- 2 staff users and 3 merchant users;
- 3 merchants with Basic/Growth/Premium variants;
- one outlet and QRIS profile per merchant;
- 60 orders and 60 payments across 12 named scenarios;
- alerts, labels, settlements, countries, audit events;
- 3 federated nodes and an initial round.

Seed timestamps are fixed around 14 July 2026 for deterministic demonstrations. Dashboard period filters may therefore need `30d` or custom dates depending on current date and seed behavior.
