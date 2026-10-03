# Deployment VPS FinGraph QRIS

Dokumen ini adalah jalur utama deployment. FinGraph QRIS merupakan
deployment-ready MVP dengan konfigurasi production-like, bukan sistem
pembayaran production yang sudah terhubung ke PJP/Bank Indonesia.

## 1. Arsitektur yang dijalankan

```text
Internet
  -> Cloudflare Tunnel (cloudflared Compose)
       -> http://reverse-proxy:8080 (Docker edge network)
            |-- /       -> frontend:3000
            `-- /api/   -> backend:8000
                              |-- postgres:5432
                              |-- neo4j:7687
                              `-- volume artifact ML
```

Walaupun aplikasi memiliki frontend dan backend, publik hanya melihat **satu
domain**. Tidak perlu mengekspos port 3000 atau 8000 dan tidak perlu membuat
subdomain API terpisah.

## 2. Kebutuhan VPS

- Docker Engine 24+ dan Docker Compose v2.20+;
- domain dengan akses DNS;
- demo minimum 2 vCPU, RAM 4 GB, disk 20 GB;
- production-like disarankan 4 vCPU, RAM 8 GB, SSD 50 GB+.

Build backend memuat dependency ML CPU dan dapat membutuhkan ruang/waktu lebih
besar pada build pertama.

## 3. Clone dan konfigurasi

```bash
git clone URL_REPOSITORY fingraph-qris
cd fingraph-qris
cp .env.production.example .env.production
chmod 600 .env.production
```

Generate nilai berbeda untuk setiap secret:

```bash
openssl rand -hex 32
```

Edit `.env.production`:

```dotenv
APP_ENV=production
DEMO_MODE=false
ENABLE_DEMO_ENDPOINTS=false
PUBLIC_REGISTRATION_ENABLED=false
ENABLE_API_DOCS=false

TRUSTED_HOSTS=fingraph.example.com
BACKEND_CORS_ORIGINS=https://fingraph.example.com
CLOUDFLARE_TUNNEL_TOKEN=REPLACE_WITH_CLOUDFLARE_TUNNEL_TOKEN

PUBLIC_BIND_ADDRESS=127.0.0.1
PUBLIC_HTTP_PORT=18080
```

Ganti seluruh `REPLACE_*`. Jangan memakai kembali secret demo dan jangan
commit `.env.production`.

## 4. Validasi, build, dan migration

Gunakan command yang sama pada setiap deployment:

```bash
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml config

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml build

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml run --rm migrate

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production overlay starts `cloudflared` after `reverse-proxy` is healthy.
Configure the Cloudflare Tunnel public hostname's service as
`http://reverse-proxy:8080`; both containers share the `edge` Docker network.
`cloudflared` also uses a separate egress network because the edge network does
not enable IP masquerading for ordinary application containers.
The tunnel token stays in the ignored `.env.production` file and is not passed
on the command line.

`migrate` membuat tabel pada database kosong dan aman dijalankan ulang.
Production tidak menjalankan seed.

Periksa service:

```bash
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml ps

docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 cloudflared

curl -fsS http://127.0.0.1:18080/api/v1/health/live
curl -fsS http://127.0.0.1:18080/api/v1/health/ready
```

Readiness `degraded` masih dapat diterima bila penyebabnya hanya Neo4j/model
opsional. PostgreSQL yang gagal akan menghasilkan service tidak ready.

## 5. Buat admin pertama

Public registration dan demo seed sengaja nonaktif pada production. Buat admin
pertama dengan environment sementara:

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

Command idempotent untuk email admin yang sama. Ia menolak eskalasi otomatis
jika email sudah dimiliki akun non-admin.

## 6. Hubungkan domain saat port 80/443 sudah dipakai

Ini adalah pola yang direkomendasikan. Compose hanya bind ke
`127.0.0.1:18080`; Nginx/Caddy host yang sudah ada tetap memakai 80/443.

### Nginx host

```bash
sudo cp deploy/nginx/host-vps.example.conf \
  /etc/nginx/sites-available/fingraph.conf
sudo sed -i 's/fingraph\\.example\\.com/domain-anda.example/g' \
  /etc/nginx/sites-available/fingraph.conf
sudo ln -s /etc/nginx/sites-available/fingraph.conf \
  /etc/nginx/sites-enabled/fingraph.conf
sudo nginx -t
sudo systemctl reload nginx
```

Setelah DNS A/AAAA mengarah ke VPS, aktifkan HTTPS melalui mekanisme yang biasa
dipakai server (misalnya Certbot atau certificate dari load balancer). Template
repo hanya berisi HTTP host config dan tidak menyimpan certificate/private key.

### Caddy host

```caddyfile
fingraph.example.com {
    reverse_proxy 127.0.0.1:18080
}
```

Caddy dapat menangani certificate otomatis jika DNS dan firewall benar.

### Mengapa cukup satu proxy_pass?

Nginx/Caddy host meneruskan seluruh request ke reverse proxy Compose.
Reverse proxy Compose kemudian merutekan:

- `/`, `/_next/*`, halaman login/dashboard -> Next.js;
- `/api/*` -> FastAPI.

Dengan demikian cookie/origin tetap konsisten dan browser tidak mengakses port
backend secara langsung.

## 7. Jika VPS belum memiliki reverse proxy

Pilihan yang lebih aman tetap memasang Nginx/Caddy host seperti langkah di
atas. Jika TLS dihentikan oleh load balancer/platform eksternal, Compose dapat
dibuka langsung:

```dotenv
PUBLIC_BIND_ADDRESS=0.0.0.0
PUBLIC_HTTP_PORT=80
```

Jangan mengekspos HTTP polos ke internet untuk penggunaan non-lokal. HSTS hanya
boleh diaktifkan setelah HTTPS benar-benar bekerja.

## 8. Firewall dan port

Port publik yang normal:

- `22/tcp` untuk SSH (atau port administrasi pilihan);
- `80/tcp` untuk ACME/redirect;
- `443/tcp` untuk HTTPS.

Jangan membuka `18080`, `3000`, `8000`, `5432`, `7474`, atau `7687` ke
internet. Binding `127.0.0.1:18080` mencegah port aplikasi diakses dari luar.

## 9. Smoke test production

Setelah HTTPS aktif:

```bash
DEMO_MODE=false ./scripts/smoke-test.sh https://fingraph.example.com
```

Smoke test memeriksa landing page, same-origin API, health, endpoint sensitif,
dan memastikan mutation Demo Lab tidak tersedia.

## 10. Demo VPS (bukan production)

Gunakan hanya untuk penjurian/sandbox:

```bash
cp .env.demo.example .env
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml up -d --build
docker compose --env-file .env --profile demo-seed \
  -f docker-compose.yml -f docker-compose.demo.yml run --rm seed-demo
DEMO_MODE=true ./scripts/smoke-test.sh http://localhost
```

Jangan memakai `.env.demo.example` atau `password123` untuk deployment publik.

## 11. Update dan rollback

Sebelum update, backup database dan catat image/commit aktif:

```bash
git rev-parse HEAD
make backup-postgres
git fetch --all
# checkout tag/commit yang sudah diverifikasi
```

Kemudian ulangi `build`, `run --rm migrate`, dan `up -d`. Rollback aplikasi
dengan checkout image/commit sebelumnya. Jika migration tidak backward
compatible, restore backup PostgreSQL dan snapshot Neo4j sebelum menjalankan
versi lama.

Jangan menjalankan `docker compose down -v` pada server berdata karena opsi
`-v` menghapus seluruh named volume.

## 12. Data persisten dan artifact

Named volume:

- `fingraph-qris-postgres-data`;
- `fingraph-qris-neo4j-data`;
- `fingraph-qris-neo4j-logs`;
- `fingraph-qris-ml-artifacts`.

Training tidak berjalan saat startup. Artifact model tidak ada bukan fatal;
scoring turun ke rule/heuristic fallback. Lihat [SCORING.md](SCORING.md) dan
[BACKUP_RESTORE.md](BACKUP_RESTORE.md).

## 13. Troubleshooting singkat

```bash
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml logs \
  --tail=200 migrate backend frontend reverse-proxy
```

- Port bentrok: ubah `PUBLIC_HTTP_PORT`, jangan mengubah port internal service.
- Domain 400/invalid host: periksa `TRUSTED_HOSTS`.
- Browser gagal API: periksa `/api/v1/health/live` melalui domain yang sama.
- Backend tidak start: periksa placeholder secret dan log migration.
- Graph degraded: periksa Neo4j; fallback PostgreSQL tetap tersedia.
- UI tanpa data: production memang tidak di-seed; buat akun dan data melalui
  alur aplikasi/integrasi yang sah.

Checklist lengkap ada di [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md);
runbook harian ada di [OPERATIONS.md](OPERATIONS.md).
