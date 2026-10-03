# Constraint Compliance

Dokumen ini memetakan constraint tambahan hackathon ke implementasi yang dapat didemonstrasikan. Seluruh angka berasal dari PostgreSQL; tidak ada metric monitoring yang di-hardcode.

## Multi-Role Collaboration & Activity Monitoring

| Requirement | Implementasi | Status |
|---|---|---|
| Minimal tiga role | `merchant`, `analyst`, `admin` dengan RBAC backend | Implemented |
| Dashboard berbeda | Merchant action-first, analyst investigation-first, admin governance/activity-first | Implemented |
| Pembatasan nyata | `require_roles()` dan ownership query di backend | Implemented |
| Aktivitas terakhir | `last_login_at`, `last_activity_at`, dan audit event | Implemented |
| Monitoring admin | Pengguna aktif, aktivitas hari ini, total pengguna, merchant aktif, distribusi role, latest/top users | Implemented |
| Filter monitoring | Periode dan role mengubah query PostgreSQL | Implemented |
| Histori role akurat | `actor_role` disimpan sebagai snapshot pada audit event | Implemented |

Pengguna aktif adalah akun aktif yang melakukan request terautentikasi dalam 15 menit terakhir. `last_activity_at` ditulis maksimal sekali per menit per pengguna untuk membatasi write amplification.

Demo:

1. Login sebagai merchant dan lakukan cek pembayaran atau buka pesanan.
2. Login sebagai analyst dan buka investigasi.
3. Login sebagai admin lalu buka **Activity Monitoring**.
4. Ubah periode dan role; angka dan daftar harus berubah.
5. Coba endpoint monitoring dengan token merchant/analyst; API mengembalikan 403.

## Smart Impact Dashboard & Action Log

| Requirement | Implementasi | Status |
|---|---|---|
| Empat metrik | Dana diterima, pembayaran berhasil, perlu diperiksa, disarankan ditahan | Implemented |
| Dua filter aktif | Periode + outlet + prioritas; seluruhnya dikirim ke backend | Implemented |
| Detail wajib | Nama item/reference, kategori, status, prioritas, waktu, tindakan | Implemented |
| Agregasi scalable | SQL aggregation dan server-side pagination, bukan limit 100 + filter browser | Implemented |
| Action Log terintegrasi | Item dampak/payment menaut ke audit entity; log memuat konteks nominal dan impact | Implemented |

Kategori bersifat opsional dengan default aman `Umum`. Prioritas adalah field eksplisit yang diturunkan secara deterministik dari risk level dan disinkronkan pada scoring.

## Bukti test

- Backend menguji 403 admin endpoint, distribusi role, filter periode/role, lebih dari 100 transaksi, serta filter outlet/prioritas.
- Frontend menguji routing beranda per role dan akses menu Activity Monitoring.
- Migration `20260723_0004` menambah field secara backward-compatible dan mengisi data lama.
