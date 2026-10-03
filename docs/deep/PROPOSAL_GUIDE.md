# TrustLens Proposal Guide

## Document identity

The 49-page submission presents **TrustLens: Website Deteksi Fraud Transaksi Keuangan Real-Time Berbasis Graph Neural Network dan Federated Learning dengan Cross-Border Intelligence untuk Meningkatkan Keamanan dan Kepercayaan Finansial UMKM Solo Raya**.

The proposal team is SpeedWin. It frames TrustLens under SDG 8, with supporting references to SDG 9 and SDG 16 in the sustainability appendix.

## Executive summary

TrustLens is proposed as a web-based financial fraud-detection platform for banks, fintechs, payment gateways, Islamic financial institutions, and MSMEs. Its central argument is that conventional systems are reactive and transaction-centric, while modern fraud operates through relationships such as mule accounts, transfer chains, shared devices, phishing, and cross-institution activity.

The intended output is:

- fraud risk score;
- Low/Medium/High risk class;
- alert;
- graph visualization;
- explanation;
- preventive recommendation.

GNN is proposed for relationship learning. Federated Learning is proposed for collaboration without centralizing raw institutional data. Cross-Border Intelligence is proposed for broader geographic/platform risk.

## Problem statement and target beneficiary

The proposal narrows the target to MSMEs in Solo Raya using QRIS, bank transfers, e-wallets, marketplaces, and payment gateways. Practical fraud examples include:

- fake transfer/payment proof;
- fictitious orders;
- manipulated buyer identity;
- suspicious repeated transactions;
- account or device abuse;
- phishing and social engineering;
- fake invoices or changed supplier accounts;
- QRIS redirection;
- account takeover.

The operational problem is not only loss. Manual verification consumes time, delays fulfillment, interrupts cash flow, creates psychological pressure, harms reputation, and can discourage digital-payment adoption.

## Economic and social framing

The proposal argues that MSMEs matter because of their national GDP and employment contribution, while Solo's MSME population and digital economy are growing. QRIS adoption expands opportunity but also the surface exposed to fraud.

The expected outcome is safer digital commerce, higher trust, less manual investigation, lower loss, and stronger local economic resilience. These are impact hypotheses, not measured outcomes of the current MVP.

## Evidence section

The PDF combines:

- government and regulator statistics;
- news/public reporting;
- charts of scam reports and public complaints;
- bank interview/desk-research material;
- team-created business and strategy analysis.

Before presenting any number, verify source, period, unit, and whether the value is national, institutional, or simulated. Avoid converting a cumulative number into a daily or annual number without source support.

## Proposed solution

The proposal's ideal flow is:

1. ingest transaction, account, and device data;
2. validate, clean, standardize, deduplicate, and engineer features;
3. construct a graph of accounts, devices, merchants, IPs, channels, places, and countries;
4. run Logistic Regression, XGBoost, and GraphSAGE;
5. compare score with threshold;
6. approve safe transactions or open alert/label workflows;
7. add cross-border and risk-configuration context;
8. return score plus approve/hold/block decision;
9. feed verified labels back into model improvement.

The repository implements a narrower QRIS version of this flow with a provider simulator and explicit merchant order state.

## Proposal ERD

The PDF diagram centers `Transactions` and connects users, accounts, devices, merchants, alerts, labels, graph relations, cross-border summaries, and settings. It is an earlier conceptual schema.

Current code retains some legacy entities but adds a more concrete QRIS domain:

- merchant profiles and outlets;
- QRIS profiles;
- orders and payment events;
- settlements;
- federated nodes and rounds;
- scoped audit logs.

Use the current SQLAlchemy models when answering implementation questions, not the PDF ERD alone.

## Technical approach in the proposal

The PDF names:

- Python and FastAPI;
- PostgreSQL and Neo4j;
- PyTorch and PyTorch Geometric;
- scikit-learn;
- MLflow;
- Flower/FedAvg;
- Next.js and Cytoscape.js;
- Docker and Kubernetes;
- MinIO;
- Prometheus and Grafana.

This list mixes current, prototype, and target technologies. FastAPI, PostgreSQL, optional Neo4j, PyTorch, scikit-learn, Next.js, Cytoscape, and Docker appear in the repository. PyTorch Geometric, MLflow, Flower, Kubernetes, MinIO, Prometheus, and Grafana do not.

## Algorithm rationale

The proposal assigns different jobs to model families:

- Logistic Regression: simple, fast tabular baseline.
- XGBoost: nonlinear tabular fraud patterns.
- GraphSAGE/GNN: connected-entity patterns.
- FedAvg: collaborative model improvement without pooling raw rows.

That division is conceptually sound. Current implementation preserves it as separate experiments rather than pretending one model solves every layer.

## Data proposal

Ideal inputs include transaction amount/time/location/method, account profile and history, device fingerprint, account-to-account transfers, shared devices, IP relationships, external blacklists/geolocation, and verified labels.

Current QRIS demo uses expected/paid amount, provider callback state, payer pseudonym, merchant/outlet/QRIS profile, region/country, order timing, transaction history, alerts, and feedback labels. It does not ingest core-banking, real device-fingerprint, or external blacklist feeds.

## Security and scalability proposal

The PDF proposes encryption, role-based access, federated privacy, modular microservices, distributed graph/learning, and global scale. The repository implements several MVP controls, but it is a modular monolith rather than a deployed microservice platform. Scalability language should remain a design direction.

## Impact and five-month roadmap

The roadmap progresses through:

1. preparation and web/model testing;
2. bank/fintech implementation;
3. advanced GNN and anomaly detection;
4. federated learning and regulator collaboration;
5. global expansion.

The repository supports stage-one MVP evidence and pieces of stages three/four as prototypes. It does not prove bank deployment, regulator collaboration, or global standardization.

## Innovation and competitor comparison

The proposal claims differentiation through the combined presence of:

- real-time detection;
- adaptive learning;
- privacy-preserving AI;
- graph-based detection;
- GNN;
- cross-border focus.

Competitor logos and checkmarks provide positioning, not a rigorous market study. Before using that slide, verify current competitor capabilities and avoid stating that competitors categorically lack features without evidence.

## Bank validation appendix

### BSI material

The BSI section explains layered bank controls, near-real-time monitoring, investigation delays, privacy practices, operational/reputational impact, multi-party fraud, regulation, interbank coordination, GNN relevance, federated learning potential, cross-border threats, MSME fraud, financing risk, and desired future features.

Much of it reads as structured desk research rather than a verbatim interview. Use it as domain synthesis unless the team can prove interviewer, participant, consent, and transcript provenance.

### Bank Muamalat transcript

The branch perspective emphasizes centralized detection, local prevention/education, phishing/skimming, the desire for same-day early warning, and reputational impact. It supports the problem of delayed branch visibility.

### Bank Mega Syariah transcript

The respondent describes an existing but non-real-time centralized system, strong bank-secrecy concerns, internal audit, OJK controls, QRIS/UMKM risk, and desire for faster detection. The response to Federated Learning does not demonstrate understanding of the concept; do not treat it as validation of the technical mechanism.

### Proper conclusion

The interviews support demand for speed, explainability, privacy, and coordination. They do not prove that any named bank has agreed to pilot, buy, integrate, or endorse TrustLens.

## Website appendix

Pages 41–44 show an earlier dark UI with login, profile, system configuration, dashboards, transactions, alerts, graph explorer, cross-border intelligence, labeling, simulation, risk map, and audit log.

Current FinGraph code covers most functional themes but uses a newer role-specific interface. Use live current screenshots for implementation evidence.

## Fishbone analysis

The fishbone groups root causes into:

- **security:** networked modern fraud and weak international intelligence;
- **privacy:** sharing restrictions and central-data breach risk;
- **economics:** direct loss, investigation cost, and reduced trust;
- **technology:** batch processing and weak relationship analysis.

This supports why the solution combines real-time workflow, graph analysis, and privacy-preserving collaboration.

## Triple Bottom Line

- **Planet:** paperless investigation and claimed lower data-transfer/resource waste.
- **People:** safety, trust, privacy, collaboration, and financial inclusion.
- **Profit:** fraud-loss reduction, operational efficiency, and scalable cost.

The environmental claim needs measurement. Federated learning can reduce raw-data transfer but may also add repeated local computation; do not assume it is automatically greener.

## PESTEL analysis

- **Political:** public support for financial-system resilience.
- **Economic:** large fraud losses and operational cost.
- **Social:** adoption depends on trust.
- **Technological:** AI and real-time detection opportunities.
- **Environmental:** digital workflows may reduce physical resources.
- **Legal:** privacy and regulatory compliance are mandatory.

PESTEL describes external conditions, not product validation.

## Best way to present the proposal

Separate three layers on every slide:

1. **Observed problem:** supported by sources and interviews.
2. **Current MVP evidence:** demonstrated directly from repository behavior.
3. **Target architecture/roadmap:** clearly labeled future integration.

That separation makes the team credible and gives judges a clean answer when they ask what works today.
