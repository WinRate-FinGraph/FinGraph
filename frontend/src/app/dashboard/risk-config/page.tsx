import { PageHeader, SummaryStrip } from "@/components/product/ui";

export default function RiskConfigPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Konfigurasi Risiko"
        description="Tinjau ambang penilaian yang digunakan oleh seluruh worker backend."
      />
      <SummaryStrip
        items={[
          { label: "Risiko rendah", value: "< 0,40", tone: "success" },
          { label: "Perlu diperiksa", value: "0,40–0,69", tone: "warning" },
          { label: "Berisiko", value: "≥ 0,70", tone: "danger" },
          { label: "Mode", value: "Environment" },
        ]}
      />
      <section className="rounded-xl border border-warning/25 bg-warning-soft p-5 text-sm leading-6">
        <h2 className="font-medium text-foreground">
          Perubahan dilakukan melalui konfigurasi service
        </h2>
        <p className="mt-1.5 text-muted-foreground">
          MVP belum menyediakan penyimpanan perubahan threshold dari antarmuka.
          Admin mengubah <code>QRIS_LOW_THRESHOLD</code>,{" "}
          <code>QRIS_HIGH_THRESHOLD</code>, dan{" "}
          <code>QRIS_ALERT_MIN_SCORE</code> pada environment lalu memulai ulang
          backend. Tidak ada kontrol palsu pada halaman ini.
        </p>
      </section>
    </div>
  );
}
