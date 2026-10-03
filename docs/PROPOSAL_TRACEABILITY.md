# Proposal Traceability

| Klaim proposal | Implementasi | Status | Demonstrasi |
|---|---|---|---|
| Real-time QRIS | Signed webhook Simulasi PJP, idempotency, replay guard | simulated | Generate payment lalu kirim webhook |
| UMKM beneficiary | Merchant mobile dashboard, order/check/alert/action/report | implemented | Login merchant |
| Fraud risk score | Explainable weighted ensemble + critical floor | implemented | Detail payment |
| Low/Medium/High | Threshold env dan badge Bahasa Indonesia | implemented | Demo Lab |
| Preventive action | Approve/verify/hold/do-not-release/report | implemented | Detail payment |
| Logistic Regression/XGBoost | QRIS synthetic logistic + PaySim pipelines | prototype | Admin train endpoint |
| Adaptive learning | Valid label counts, one-class/minimum guard, artifact | prototype | Adaptive Learning page |
| Graph intelligence | QRIS nodes/edges, heuristic, Neo4j + PG fallback | implemented | Graph Intelligence |
| GNN/GraphSAGE | QRIS training pipeline, signed artifact/status, 50% final-score blend by default when active; legacy fallback | experimental on synthetic data | Model AI endpoint and payment scoring |
| Federated Learning/FedAvg | 3 node, weighted parameter aggregation, DB rounds | prototype | Federated Learning page |
| Privacy preserving | Keyed pseudonym, masked account, no raw FedAvg rows | implemented | Privacy summary |
| Cross-Border | Region/country/routes/timeline/high-risk aggregation | implemented with demo data | Cross-Border page |
| PostgreSQL/FastAPI/Next.js/Neo4j/Cytoscape/Docker | Full stack dan compose namespaced | implemented | Start Compose |
| Audit/RBAC | Auth dependency, role checks, ownership, audit | implemented | Isolation tests/audit page |
| Multi-role dashboard | Merchant, analyst, dan admin memiliki beranda dan information architecture berbeda | implemented | Login ketiga role dan bandingkan dashboard |
| Activity monitoring admin | Aktivitas DB real-time, active user 15 menit, distribusi snapshot role, filter periode/role | implemented | Menu Activity Monitoring sebagai admin |
| Smart Impact Dashboard | Agregasi server-side, 4 metrik, filter periode/outlet/prioritas, detail kategori/prioritas/action | implemented | Beranda merchant dan Laporan |
| Integrated Action Log | Tautan payment-impact ke audit scope dan konteks nominal/status pada log | implemented | Klik “Riwayat” pada item dampak |
| Official BI/PJP connection | Tidak tersedia; selalu diberi label Mode Demo | roadmap | Landing/help notice |
| Production secure aggregation/DP | Belum diterapkan | roadmap | Federated limitation note |
