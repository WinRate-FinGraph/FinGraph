# API Integration

## Paket merchant

- `GET /api/v1/merchants/subscription` mengembalikan paket aktif, limit, katalog,
  serta status ketersediaan checkout.
- `PATCH /api/v1/merchants/subscription` mengubah entitlement hanya pada Mode
  Demo dan tidak memproses pembayaran.
- `/api/v1/auth/me` menyertakan `subscription_plan` dan metadata subscription.
- Laporan lengkap, export, dan merchant Action Log memerlukan minimal Growth.


Base URL browser/deployment adalah same-origin `/api/v1` (contoh `http://localhost/api/v1`). Port `8000` hanya digunakan saat development backend langsung. Login mengembalikan bearer JWT. Credential pada contoh berikut hanya tersedia setelah seed eksplisit di Mode Demo; jangan gunakan pada production.

```bash
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"merchant@fingraph.id","password":"password123"}' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/merchants/dashboard
```

Endpoint utama: `/auth`, `/merchants`, `/orders`, `/payments`, `/alerts`, `/labels`, `/graph`, `/cross-border`, `/ml`, `/federated`, `/reports`, `/audit-logs`, `/admin`, dan `/demo/qris`. OpenAPI adalah kontrak field lengkap.

## Ringkasan publik landing page

`GET /api/v1/public/trust-summary` tidak memerlukan autentikasi dan hanya
mengembalikan agregat anonim untuk social proof landing page:

- jumlah akun aktif yang terdaftar;
- jumlah pengguna aktif dalam jendela 15 menit;
- jumlah merchant dan outlet aktif;
- jumlah payment event yang sudah diperiksa;
- jumlah serta persentase pembayaran sukses berisiko rendah.

Angka dihitung langsung dari database dan landing page memperbaruinya setiap 30
detik. Endpoint tidak mengembalikan email, nama, pseudonim pembayar, referensi,
atau identifier lainnya. Pada Mode Demo, response dan UI diberi label `Mode
Demo`; angka tersebut adalah data seed/simulasi, bukan klaim jumlah pelanggan
production.

## Activity Monitoring dan Smart Impact

`GET /api/v1/admin/activity-monitoring` hanya dapat diakses admin. Parameter yang didukung:

- `period=today|7d|30d|custom`
- `role=merchant|analyst|admin`
- `date_from` dan `date_to` untuk periode custom
- `limit` untuk aktivitas terbaru

Respons berisi pengguna aktif, aktivitas hari ini, total pengguna, merchant aktif, distribusi per role, aktivitas terbaru, dan pengguna paling aktif. Pengguna aktif didefinisikan sebagai akun `is_active=true` yang mempunyai aktivitas dalam 15 menit terakhir. Distribusi memakai snapshot `actor_role` pada audit event.

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost/api/v1/admin/activity-monitoring?period=7d&role=merchant"
```

`GET /api/v1/reports/impact-dashboard` melakukan filter dan agregasi di database. Parameter: `period`, `outlet_id`, `priority`, `payment_status`, `category`, custom dates, `limit`, dan `offset`. Merchant otomatis di-scope ke usahanya; analyst/admin harus menentukan merchant. Response mencakup empat metrik utama, timeline, distribusi prioritas, insight, item dampak, dan pagination.

`GET /api/v1/audit-logs` mendukung parameter periode/role/entity dan mengembalikan ringkasan activity monitoring pada scope yang diizinkan. Merchant hanya menerima audit miliknya.

Webhook signature:

```python
import hashlib, hmac, json
body = {"provider_reference":"...", "payment_status":"success", "amount":350000,
        "currency":"IDR", "merchant_code":"...", "outlet_code":"...",
        "nmid":"...", "qr_fingerprint":"...", "timestamp": 1784040000}
canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
signature = hmac.new(PJP_SIMULATOR_SECRET.encode(), canonical, hashlib.sha256).hexdigest()
```

Kirim JSON tanpa perubahan dengan `Authorization: Bearer ...` dan `X-PJP-Signature: <signature>`. Demo mutation tetap authenticated. Production seharusnya memakai mTLS/provider credential terpisah, bukan JWT merchant.
