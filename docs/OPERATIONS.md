# Operations Runbook

## Status dan log

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=200 reverse-proxy frontend backend gnn-worker migrate
curl -fsS https://qris.example.com/api/v1/health/live
curl -fsS https://qris.example.com/api/v1/health/ready
```

Jika domain dilayani Nginx/Caddy host, cek kedua lapisan:

```bash
curl -fsS http://127.0.0.1:18080/api/v1/health/live
curl -fsS https://qris.example.com/api/v1/health/live
```

Log container dirotasi 10 MB, maksimal tiga file. Request API memiliki request ID dan response mengirim `X-Request-ID`. Body autentikasi, token, secret webhook, dan raw callback tidak dicatat.

## Interpretasi readiness

- HTTP 200 `ready`: database siap dan optional components tersedia.
- HTTP 200 `degraded`: database siap, tetapi Neo4j atau artifact model opsional tidak tersedia. Fallback tetap bekerja.
- HTTP 503 `unavailable`: PostgreSQL tidak dapat diakses, migration tidak sesuai, atau Neo4j diwajibkan tetapi gagal.

## Restart

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml restart backend frontend reverse-proxy
```

Restart tidak menghapus volume. Jika backend gagal, periksa log `migrate`, koneksi PostgreSQL, dan validasi environment terlebih dahulu.

## Gangguan komponen

- PostgreSQL gagal: API tidak ready; jangan menerima traffic tulis. Pulihkan database/volume.
- Neo4j gagal: graph memakai fallback PostgreSQL, readiness degraded bila Neo4j opsional.
- Model hilang: scoring memakai rule/heuristic fallback; jangan klaim model aktif pada UI.
- Frontend gagal menjangkau API: periksa health backend, upstream Nginx, dan routing `/api/`.
- Domain gagal tetapi loopback `18080` sehat: periksa konfigurasi host
  Nginx/Caddy, DNS, certificate, dan firewall.

## Scaling

Backend workers dikontrol `UVICORN_WORKERS`. Migration tetap one-shot sebelum backend. Jangan menjalankan seed sebagai startup hook. Jika menambah replica, gunakan load balancer dan external store untuk rate limit/idempotency sebelum beban produksi besar.

## Secret rotation

Ubah secret melalui secret manager/`.env.production`, restart service terkait, lalu validasi smoke test. Rotasi JWT memutus token aktif. Rotasi PJP secret harus dikoordinasikan dengan integrator webhook. Jangan mencetak nilai secret ke terminal bersama/log.
