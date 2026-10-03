# Security

Kontrol MVP: bcrypt password, JWT env secret, backend RBAC, ownership filter merchant pada payment/order/alert/label/report/audit/graph, HMAC webhook, constant-time compare, timestamp/replay protection, provider-reference uniqueness, idempotency, Pydantic bounds, ORM, pagination max 100, CORS allowlist, masked settlement account, keyed-HMAC payer pseudonym, sanitized callback storage, dan audit action penting.

Jangan log atau commit `.env`, token, key, raw payer, raw callback, dataset, atau artifact. Jangan membawa credential demo ke deployment production. Gunakan HTTPS, KMS/HSM, short-lived token + refresh rotation, Redis-backed rate limit/idempotency, CSP/security headers, secret scanning, dependency/SBOM scanning, central audit/SIEM, backup encryption, dan retention policy untuk production.

Threats yang diuji: merchant mengganti UUID milik merchant lain, signature invalid, callback replay, callback duplikat/berbeda, reference reuse, QR mismatch, nominal mismatch, dan payer berjejaring. Known limitation: rate limiting distributed, secure aggregation, differential privacy, dan official PJP verification belum tersedia.
