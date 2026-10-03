# QRIS Demo Flow

1. Merchant membuat order dan memilih outlet.
2. Simulator membuat `PaymentEvent(pending)` serta payload signed webhook.
3. Webhook memverifikasi HMAC canonical JSON, timestamp tolerance, ownership, reference, dan idempotency.
4. Callback valid memperbarui status, membangun feature, menghitung rule/tabular/adaptive/graph, lalu menerapkan critical floor.
5. Medium/high membuat alert. Order menjadi `paid` hanya untuk success low-risk; medium/high menjadi `held`.
6. Event dicatat pada audit dan disinkronkan ke Neo4j secara best effort.
7. Merchant memilih approve/verify/hold/report; label valid masuk feedback loop.

`fake_receipt` sengaja tidak memiliki callback dan menghasilkan `CALLBACK_NOT_FOUND`. `cross_region` hanya sinyal kecil. `cross_border` membuka analitik rute tanpa auto-block. Seluruh hasil berlabel Mode Demo dan tidak merepresentasikan status jaringan QRIS nyata.

Payload authenticity check menerima string hasil decode. FinGraph membandingkan fingerprint, NMID/profil yang dipilih, outlet, tipe, dan acquirer yang tersimpan. MVP tidak menyediakan upload gambar karena decoder belum dijamin stabil.
