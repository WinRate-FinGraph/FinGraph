# Arsitektur FinGraph QRIS

FinGraph QRIS memisahkan dua pengalaman di satu platform: merchant mendapat UI singkat dan ownership-scoped; analyst/admin mendapat investigasi dan intelligence global. Authorization tetap dilakukan backend.

```text
Next.js (browser + local JWT)
  -> FastAPI /api/v1
     -> PostgreSQL: user, merchant, outlet, QRIS, order, payment, alert,
                    label, settlement, audit, federated metadata
     -> Neo4j: Payer/Payment/Order/Merchant/Outlet/QRIS/PJP/Region/Country
     -> Scoring: rule 35 + tabular 30 + graph 25 + adaptive 10
     -> PJP simulator: canonical JSON + HMAC + timestamp + idempotency
     -> FedAvg simulator: weighted local parameter aggregation
```

PostgreSQL adalah source of truth. Neo4j dapat gagal tanpa menjatuhkan transaksi; explorer memakai graph PostgreSQL fallback. Artifact ML disimpan lokal/volume, bukan database/Git. GraphSAGE hanya di-inferensikan bila artifact tersedia; keputusan MVP tetap memakai graph heuristic.

Model lama `Transaction/Account/Device/Merchant` dipertahankan untuk benchmark/admin. Domain QRIS baru memakai tabel terpisah agar migration tidak kehilangan data. Role lama dinormalisasi ke lowercase; `INSTITUTION`/`OPERATOR` menjadi merchant.

Boundary privasi: raw payer masuk hanya saat request simulator, langsung menjadi keyed-HMAC pseudonym; callback yang disimpan hanya field operasional dan SHA-256 hash payload canonical. Neo4j menerima pseudonym, bukan identifier mentah. Federated aggregator menerima parameter dan sample count, bukan row.

## Multi-role dan monitoring aktivitas

Tiga role menggunakan pengalaman yang berbeda:

- Merchant: kondisi pembayaran, pesanan, peringatan, laporan dampak, dan action log miliknya.
- Analyst: investigasi global, graph, lintas wilayah, dan monitoring model.
- Admin: governance platform, activity monitoring, konfigurasi risiko, serta fitur analyst.

Otorisasi tetap diperiksa di backend melalui `require_roles()` dan merchant ownership scope. Admin Activity Monitoring hanya menerima role `admin`; menu frontend bukan lapisan keamanan.

Login mengisi `last_login_at`. Request terautentikasi mengisi `last_activity_at` paling sering satu kali per menit agar aktivitas tercatat tanpa write database pada setiap request. Pengguna aktif berarti akun aktif dengan `last_activity_at` dalam 15 menit terakhir. Jendela ini cukup responsif untuk demonstrasi kolaborasi, tetapi tidak menganggap tab lama sebagai sesi aktif tanpa batas.

Setiap audit event menyimpan `actor_role` sebagai snapshot historis. Perubahan role pengguna sesudah event tidak mengubah distribusi aktivitas masa lalu. Monitoring dan Action Log mengambil agregasi langsung dari PostgreSQL, bukan data statis.

Smart Impact Dashboard menggunakan agregasi SQL berdasarkan periode, outlet, prioritas, status pembayaran, dan kategori. Frontend hanya mengambil halaman detail yang diperlukan; metrik tidak dihitung dari potongan 100 transaksi. Prioritas tersimpan eksplisit dengan pemetaan `low → rendah`, `medium → sedang`, dan `high → tinggi`.
