# FinGraph QRIS

FinGraph QRIS adalah asisten keamanan pembayaran bagi UMKM: **pastikan
pembayaran masuk sebelum pesanan diserahkan**. Merchant mendapat keputusan dan
tindakan yang mudah dipahami, sementara analyst dan admin mendapat investigasi,
graph, model monitoring, audit, dan activity monitoring sesuai perannya.

Status proyek: **deployment-ready MVP dengan konfigurasi production-like**.
QRIS/PJP masih berupa simulator; aplikasi belum terhubung ke Bank Indonesia,
bank, atau PJP nyata.

Untuk memahami proyek sebelum presentasi, mulai dari
[arsitektur](docs/ARCHITECTURE.md),
[scoring](docs/SCORING.md), dan
[traceability proposal](docs/PROPOSAL_TRACEABILITY.md).

## Mulai dari sini

Pilih satu workflow:

| Tujuan | Gunakan |
|---|---|
| Coba seluruh fitur dan data contoh | [Docker demo](#docker-demo-paling-cepat) |
| Jalankan source saat development | [Development lokal](#development-lokal) |
| Pasang pada VPS dan domain | [Deployment VPS](#deployment-vps-production-like) |
| Vercel + backend/database terkelola | [Panduan Vercel](docs/VERCEL_MANAGED_BACKEND.md) |

## Arsitektur

```text
Browser
  -> satu domain / reverse proxy
       |-- /          -> Next.js frontend
       `-- /api/      -> FastAPI backend
                            |-- PostgreSQL (system of record)
                            |-- Neo4j (opsional, ada fallback)
                            `-- volume artifact ML
```

Browser tidak perlu membuka port backend. PostgreSQL dan Neo4j juga tidak
dipublikasikan pada konfigurasi production.

Fitur utama:

- dashboard berbeda untuk `merchant`, `analyst`, dan `admin`;
- RBAC dan ownership validation di backend;
- QRIS guard, fraud/risk score, alasan, rekomendasi, dan alert;
- Smart Impact Dashboard dengan filter dan agregasi server-side;
- Action Log, activity monitoring admin, laporan, graph, dan lintas wilayah;
- prototype GraphSAGE, adaptive learning, dan FedAvg;
- paket Basic Rp49.000, Growth Rp99.000, dan Premium Rp149.000/bulan.

## How the backend assesses payment risk

The backend does not make a verified binary “fraud or genuine” decision. It builds a risk score from payment checks and behavior signals, then returns a risk level and recommended action. Critical checks include missing provider confirmation, unsuccessful payment status, amount or merchant/QR mismatch, duplicate references, and replayed callbacks. A cross-region or cross-border payment is only a weak signal, not proof of fraud.

The legacy score combines rule checks (35%), tabular ML (30%), graph heuristic (25%), and adaptive ML (10%). On the `GNN-implementation` branch, an active GraphSAGE model contributes 50% of the final score and the legacy ensemble supplies the other 50%. QRIS GNN inference is enabled by default; if no active artifact exists or inference fails, scoring falls back to the legacy ensemble and reports that state. Medium/high/critical rule findings still impose score floors. With the default thresholds, scores below 0.40 are low risk, 0.40–0.69 medium, and 0.70 or above high.

These scores are risk indicators, not calibrated probabilities. “Low risk” or “approve” does not prove a payment is genuine, and “high risk” is a reason to review or hold it—not a confirmed fraud finding. Synthetic dataset labels are also only simulator labels: see the [dataset README](datasets/synthetic-qris-v2/README.md).

## Synthetic QRIS training data

Synthetic labels are assigned by the generator, not inferred from payment details: with the default 10% setting, it randomly selects 5,000 of 50,000 rows as injected scenarios (`label=1`) and marks the rest as generated baseline (`label=0`). A positive label is not confirmed fraud; a zero label is not verified genuine. See the [dataset README](datasets/synthetic-qris-v2/README.md) for exact rules, scenario types, and limitations.

Paket saat ini merupakan entitlement MVP; payment gateway dan penagihan
otomatis belum diimplementasikan.

## Docker demo paling cepat

Prasyarat: Docker Engine 24+ dan Docker Compose v2.20+.

```bash
cp .env.demo.example .env
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml up -d --build
docker compose --env-file .env --profile demo-seed \
  -f docker-compose.yml -f docker-compose.demo.yml run --rm seed-demo
DEMO_MODE=true ./scripts/smoke-test.sh http://localhost
```

Buka `http://localhost`. Seed bersifat eksplisit dan idempotent.

Untuk production melalui Cloudflare Tunnel, isi
`CLOUDFLARE_TUNNEL_TOKEN` pada `.env.production`, lalu jalankan stack dengan
`docker-compose.prod.yml`. Service `cloudflared` sudah berada pada network
Docker yang sama dan meneruskan public hostname ke
`http://reverse-proxy:8080`. Jangan commit credential tunnel.

| Peran | Email | Password demo lokal |
|---|---|---|
| Merchant | `merchant@fingraph.id` | `password123` |
| Analyst | `analyst@fingraph.id` | `password123` |
| Admin | `admin@fingraph.id` | `password123` |

Credential tersebut hanya untuk Mode Demo dan tidak dibuat pada production.

## Development lokal

Prasyarat: Python 3.11, Node 20+, PostgreSQL, dan Neo4j opsional.

Backend:

```bash
cd backend
cp .env.example .env
python3.11 -m pip install --user --break-system-packages \
  -r requirements.txt -r requirements-dev.txt
python3.11 -m alembic upgrade head
python3.11 -m app.db.seeds.seed        # hanya jika butuh data demo
python3.11 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend pada terminal lain:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Buka `http://localhost:3000`. Frontend meneruskan `/api/*` ke
`http://127.0.0.1:8000`.

## Deployment VPS production-like

Panduan lengkap dan troubleshooting ada di [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
Alur utamanya:

```bash
cp .env.production.example .env.production
# Isi domain dan ganti SEMUA REPLACE_* dengan secret unik:
openssl rand -hex 32

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml config
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml build
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Inisialisasi database

`migrate` membuat seluruh tabel dari database kosong dan aman dijalankan ulang.
Production tidak menjalankan seed. Buat admin pertama melalui command satu-kali:

```bash
read -rp "Email admin: " FINGRAPH_ADMIN_EMAIL
read -rp "Nama admin: " FINGRAPH_ADMIN_NAME
read -rsp "Password admin (min. 12 karakter): " FINGRAPH_ADMIN_PASSWORD; echo
export FINGRAPH_ADMIN_EMAIL FINGRAPH_ADMIN_NAME FINGRAPH_ADMIN_PASSWORD

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml run --rm \
  -e FINGRAPH_ADMIN_EMAIL -e FINGRAPH_ADMIN_NAME -e FINGRAPH_ADMIN_PASSWORD \
  backend python -m app.db.create_admin

unset FINGRAPH_ADMIN_EMAIL FINGRAPH_ADMIN_NAME FINGRAPH_ADMIN_PASSWORD
```

Bootstrap menolak mengubah akun non-admin menjadi admin dan tidak pernah
mencetak password.

### Jika port 80/443 VPS sudah dipakai

Tidak perlu membuka dua domain atau dua port untuk frontend/backend. Biarkan
Nginx/Caddy host yang sudah ada tetap memegang 80/443, lalu jalankan stack pada
loopback:

```dotenv
PUBLIC_BIND_ADDRESS=127.0.0.1
PUBLIC_HTTP_PORT=18080
TRUSTED_HOSTS=fingraph.example.com
BACKEND_CORS_ORIGINS=https://fingraph.example.com
```

Copy `deploy/nginx/host-vps.example.conf` ke konfigurasi Nginx host, ganti
`fingraph.example.com`, lalu aktifkan HTTPS. Nginx host meneruskan seluruh
domain ke `127.0.0.1:18080`; reverse proxy di dalam Compose yang membagi `/`
ke frontend dan `/api/` ke backend.

Verifikasi sebelum membuka traffic:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health/live
curl -fsS http://127.0.0.1:18080/api/v1/health/ready
DEMO_MODE=false ./scripts/smoke-test.sh https://fingraph.example.com
```

Jangan membuka port 3000, 8000, 5432, 7474, atau 7687 di firewall production.

## Environment

- Root `.env`: Docker demo, dibuat dari `.env.demo.example`.
- Root `.env.production`: Docker VPS, dibuat dari `.env.production.example`.
- `backend/.env`: development backend tanpa Docker.
- `frontend/.env`: development frontend atau Vercel.

Semua file `.env` nyata diabaikan Git. Hanya template tersanitasi yang
di-commit. Production menolak secret placeholder/lemah, demo endpoint, public
registration, dan auto-seed.

## Health dan fallback

- `/api/v1/health/live`: proses backend hidup.
- `/api/v1/health/ready`: PostgreSQL wajib siap.
- Neo4j atau artifact ML opsional dapat menghasilkan `degraded`; rule-based dan
  PostgreSQL graph fallback tetap berjalan.
- Training dan seed tidak berjalan otomatis saat startup.

## Validasi sebelum push/deploy

```bash
make check
make test
make build
make docker-config
make docker-build
make smoke
git diff --check
```

Jangan menjalankan `docker compose down -v` pada deployment berdata karena
perintah itu menghapus volume.

## Dokumentasi

Untuk belajar dan menyiapkan presentasi:

1. [Arsitektur](docs/ARCHITECTURE.md)
2. [Scoring](docs/SCORING.md)
3. [Alur demo QRIS](docs/QRIS_DEMO_FLOW.md)
4. Proposal asli TrustLens tidak disertakan pada submission publik karena
   dokumen tersebut memuat data kontak kontributor.

Mulai dari tiga dokumen operasional ini:

1. [Deployment VPS](docs/DEPLOYMENT.md)
2. [Production checklist](docs/PRODUCTION_CHECKLIST.md)
3. [Operations dan troubleshooting](docs/OPERATIONS.md)

Referensi lanjutan:

- [Backup/restore](docs/BACKUP_RESTORE.md)
- [Arsitektur](docs/ARCHITECTURE.md)
- [Keamanan](docs/SECURITY.md)
- [Integrasi API](docs/API_INTEGRATION.md)
- [Scoring dan model](docs/SCORING.md)
- [Proposal traceability](docs/PROPOSAL_TRACEABILITY.md)
- [Constraint compliance](docs/CONSTRAINT_COMPLIANCE.md)
- [Paket berlangganan](docs/SUBSCRIPTION_PLANS.md)

## Batasan sebelum penggunaan nyata

Integrasi PJP resmi, secret manager/KMS, HTTPS, backup offsite, monitoring
terpusat, distributed rate limiting/idempotency, pentest, privacy/legal review,
dan disaster-recovery drill masih diperlukan sebelum menangani transaksi
production nyata.
