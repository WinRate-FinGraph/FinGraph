# Production Checklist

## Sebelum build

- [ ] `.env.production` dibuat lokal dan tidak masuk Git.
- [ ] Semua `REPLACE_*` diganti secret unik minimal 32 karakter.
- [ ] `APP_ENV=production`, `DEMO_MODE=false`, `AUTO_SEED=false`.
- [ ] Demo endpoints dan public registration nonaktif.
- [ ] `TRUSTED_HOSTS` dan CORS berisi domain eksplisit tanpa wildcard.
- [ ] Jika 80/443 sudah dipakai host proxy, Compose bind ke
      `PUBLIC_BIND_ADDRESS=127.0.0.1` pada port alternatif.
- [ ] Backup PostgreSQL dan snapshot/backup volume Neo4j tersedia.
- [ ] Artifact model yang diperlukan sudah ditempatkan pada volume; fallback telah diterima bila artifact tidak ada.

## Validasi

- [ ] `docker compose ... config` berhasil.
- [ ] Frontend/backend image berhasil dibuild.
- [ ] Migration one-shot berhasil.
- [ ] PostgreSQL, backend, frontend, dan reverse proxy healthy.
- [ ] Readiness `ready` atau `degraded` hanya karena komponen opsional yang diketahui.
- [ ] `DEMO_MODE=false ./scripts/smoke-test.sh https://domain` lulus.
- [ ] Endpoint Demo Lab mutation memberi 404.
- [ ] `/docs` nonaktif jika `ENABLE_API_DOCS=false`.
- [ ] Registration nonaktif.
- [ ] Admin awal dibuat lewat `python -m app.db.create_admin`, bukan seed demo.
- [ ] Hanya port reverse proxy yang dipublikasikan.
- [ ] Port Compose alternatif hanya listen pada `127.0.0.1`.
- [ ] UID frontend/backend bukan root.
- [ ] Log tidak memuat token, password, signature, atau secret.

## Keamanan dan operasi

- [ ] HTTPS aktif dan redirect HTTP dikonfigurasi di platform/proxy TLS.
- [ ] Firewall hanya membuka 80/443 dan port administrasi yang dibutuhkan.
- [ ] Rotation dan retensi log ditetapkan.
- [ ] Backup terjadwal diuji dengan restore berkala.
- [ ] Alert disk, CPU, memory, health, dan certificate expiry tersedia.
- [ ] Akun admin awal dibuat melalui proses terkontrol, bukan seed demo.
- [ ] Rencana rollback dan maintenance window dicatat.

FinGraph QRIS adalah MVP production-like; checklist ini tidak menggantikan audit kepatuhan, pentest, dan integrasi PJP resmi.
