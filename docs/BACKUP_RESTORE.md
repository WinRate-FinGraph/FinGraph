# Backup dan Restore

## PostgreSQL

Backup format custom:

```bash
mkdir -p backups
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > backups/fingraph-qris-$(date +%Y%m%d-%H%M%S).dump
```

Restore ke database kosong atau maintenance window:

```bash
docker compose --env-file .env.production \
  -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists < backups/FILE.dump
```

Uji restore pada environment terisolasi. Enkripsi backup, batasi akses, simpan salinan offsite, dan tetapkan retensi.

## Neo4j

Named volume `fingraph-qris-neo4j-data` menyimpan graph. Strategi yang paling portabel adalah snapshot volume saat container dihentikan secara konsisten atau backup tingkat platform. Perintah `neo4j-admin database dump` dan online backup bergantung versi/edition Neo4j; validasi terhadap image `5.26.28-community` dan lisensi sebelum digunakan.

Graph dapat dibangun ulang dari PostgreSQL melalui sync, tetapi backup tetap disarankan agar recovery lebih cepat.

## Artifact ML

Backup named volume `fingraph-qris-ml-artifacts` bersama metadata model. Artifact harus dipasangkan dengan versi aplikasi dan feature list yang kompatibel. Kehilangan volume ini tidak menghilangkan system of record; backend turun ke fallback rule/heuristic dan readiness melaporkan degraded.

## Peringatan data

`docker compose down -v` menghapus seluruh named volume. Jangan menjalankannya pada deployment produksi kecuali memang berniat menghapus data secara permanen.
