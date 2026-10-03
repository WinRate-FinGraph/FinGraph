# Paket dan entitlement FinGraph

Katalog paket pada MVP menggunakan Rupiah per bulan. Belum ada payment gateway
atau penagihan otomatis. Perubahan paket melalui UI hanya aktif pada
`DEMO_MODE=true` dan dicatat ke Action Log dengan metadata
`payment_processed=false`.

| Paket | Harga | Transaksi | Outlet | Akun | Akses utama |
|---|---:|---:|---:|---:|---|
| Basic | Rp49.000/bulan | 500/bulan | 1 | 1 merchant | Scoring dasar, dashboard ringkas, alert, rekomendasi, label |
| Growth | Rp99.000/bulan | 2.000/bulan | 3 | hingga 3 | Semua Basic, filter lengkap, kategori/prioritas, laporan, export, Action Log |
| Premium | Rp149.000/bulan | 5.000/bulan | multi outlet | 5+ | Semua Growth, admin monitoring, graph, lintas wilayah, federated, API |

## Perilaku aplikasi

- Paket disimpan pada `merchant_profiles.subscription_plan`.
- `/api/v1/auth/me` mengirim `subscription_plan` dan metadata limit.
- Akun merchant demo utama memakai Premium. Merchant demo Batik memakai Growth
  dan Kerajinan memakai Basic agar tiga tingkat dapat diperagakan.
- Analyst dan admin demo diperlakukan sebagai workspace Premium.
- Menu, kolom, filter, dan route merchant mengikuti paket aktif.
- Laporan lengkap, export, dan Action Log memerlukan minimal Growth.
- Graph, Cross-Border, Federated Learning, dan Activity Monitoring tetap
  memerlukan role teknis yang sesuai serta workspace Premium.
- Limit outlet dan transaksi simulator ditegakkan backend.
- Model seat per organisasi belum tersedia pada MVP. Role analyst/admin yang ada
  merupakan akun operasional global untuk demonstrasi RBAC, bukan billing seat
  production.

## Endpoint

```http
GET /api/v1/merchants/subscription
PATCH /api/v1/merchants/subscription
Content-Type: application/json

{"plan":"growth"}
```

`PATCH` ditolak pada production karena checkout belum tersedia. Integrasi
payment gateway, invoice, grace period, webhook billing, dan lifecycle
subscription merupakan roadmap.
