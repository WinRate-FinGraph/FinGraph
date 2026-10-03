# Deploy frontend Vercel + backend terkelola

Panduan ini memisahkan Next.js di Vercel dari FastAPI dan PostgreSQL pada
provider backend 24 jam. Neo4j tetap opsional karena PostgreSQL fallback
tersedia.

## 1. Persiapan database

Buat PostgreSQL terkelola dan simpan connection string TLS yang diberikan
provider. Database kosong diinisialisasi melalui Alembic, bukan dengan
`Base.metadata.create_all()`:

```bash
cd backend
python3.11 -m pip install --user --break-system-packages \
  -r requirements.txt -r requirements-dev.txt
cp .env.production.example .env
# Isi DATABASE_URL dan seluruh secret.
python3.11 -m alembic upgrade head
python3.11 -m alembic current
```

Untuk demo hackathon saja:

```bash
APP_ENV=demo DEMO_MODE=true QRIS_DEMO_MODE=true \
  python3.11 -m app.db.seeds.seed
```

Jangan menjalankan seed pada production. Seed bersifat idempotent, tetapi tetap
membuat akun dan data simulasi.

## 2. Deploy backend FastAPI

Provider harus mendukung:

- Python 3.11 atau container Docker;
- process yang tidak tidur untuk kebutuhan 24 jam;
- environment variables/secret manager;
- outbound PostgreSQL dan, bila dipakai, Neo4j;
- health check HTTP;
- pre-deploy/release command untuk migration.

Konfigurasi umum:

```text
Root directory : backend
Build command  : python -m pip install -r requirements.txt
Release command: python -m alembic upgrade head
Start command  : uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
Health check   : /api/v1/health/ready
```

Salin variabel dari `backend/.env.production.example` ke dashboard provider.
Jangan upload file `.env` ke Git.

Untuk deployment hackathon yang memang membutuhkan akun demo, gunakan
`APP_ENV=demo`, `DEMO_MODE=true`, `QRIS_DEMO_MODE=true`,
`ENABLE_DEMO_ENDPOINTS=true`, lalu jalankan seed sekali secara eksplisit.
Konfigurasi tersebut tetap sebuah demo publik, bukan production mode.

## 3. Deploy frontend ke Vercel

1. Import repository di Vercel.
2. Set Root Directory ke `frontend`.
3. Framework Preset: Next.js.
4. Tambahkan environment:

```text
NEXT_PUBLIC_API_URL=/api/v1
INTERNAL_API_URL=https://API-BACKEND-ANDA.example.com
NEXT_PUBLIC_DEMO_MODE=false
```

`INTERNAL_API_URL` tidak memakai suffix `/api/v1`; rewrite Next.js sudah
menambahkan path `/api/*`. Untuk demo juri, set
`NEXT_PUBLIC_DEMO_MODE=true` agar pilihan akun demo ditampilkan.

5. Deploy, lalu tambahkan domain Vercel/custom domain ke backend:

```text
TRUSTED_HOSTS=api.example.com,nama-project.vercel.app
BACKEND_CORS_ORIGINS=https://nama-project.vercel.app,https://domain-anda.id
```

Walaupun browser memakai path relatif `/api/v1`, origin frontend tetap perlu
dicatat untuk deployment preview atau bila API dipanggil langsung.

## 4. Urutan init dan update

Deployment pertama:

```bash
python -m alembic upgrade head
# opsional, demo saja:
python -m app.db.seeds.seed
```

Setiap update:

1. backup PostgreSQL;
2. deploy backend baru;
3. jalankan `python -m alembic upgrade head` sebagai release command;
4. cek `/api/v1/health/ready`;
5. deploy frontend;
6. login dan jalankan smoke route utama.

## 5. Secret

Generate nilai independen:

```bash
openssl rand -hex 32  # JWT_SECRET_KEY
openssl rand -hex 32  # PAYER_PSEUDONYM_KEY
openssl rand -hex 32  # PJP_SIMULATOR_SECRET bila demo
```

Jangan memakai password demo, placeholder `REPLACE_*`, atau secret yang sama
untuk beberapa fungsi.

## 6. Checklist setelah deploy

- `/` memuat landing FinGraph.
- `/api/v1/health/live` menghasilkan 200.
- `/api/v1/health/ready` menghasilkan ready/degraded yang terdokumentasi.
- Login dapat memanggil `/api/v1/auth/me`.
- Vercel Network tidak memanggil `localhost:8000`.
- `subscription_plan` tampil pada response user.
- Demo endpoint 404 ketika `DEMO_MODE=false`.
- API docs mati ketika `ENABLE_API_DOCS=false`.
- Database dan Neo4j tidak diekspos langsung ke browser.
