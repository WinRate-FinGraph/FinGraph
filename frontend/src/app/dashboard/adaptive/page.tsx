"use client";

import { toast } from "sonner";
import {
  DataState,
  PageHeader,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { getStoredUser } from "@/lib/auth";

type Status = {
  qris: {
    labels_available: number;
    usable_binary_labels: number;
    labels_required: number;
    ready_for_training: boolean;
    class_distribution: Record<string, number>;
  };
};

export default function AdaptivePage() {
  const query = useApi<Status>("/ml/adaptive/status");
  const user = getStoredUser();
  const status = query.data?.qris;
  async function train() {
    try {
      await apiFetch("/ml/adaptive/qris-retrain", { method: "POST" });
      toast.success("Model adaptif selesai dilatih");
      await query.reload();
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "Pelatihan belum dapat dijalankan",
      );
    }
  }
  return (
    <div className="space-y-6">
      <PageHeader
        title="Pembelajaran dari catatan"
        description="Lihat apakah catatan pemeriksaan sudah cukup untuk membantu model berikutnya."
        action={
          user?.role === "admin" ? (
            <Button disabled={!status?.ready_for_training} onClick={train}>
              Latih ulang model
            </Button>
          ) : undefined
        }
      />
      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {status && (
          <>
            <SummaryStrip
              items={[
                { label: "Label tersedia", value: status.labels_available },
                {
                  label: "Label biner valid",
                  value: status.usable_binary_labels,
                },
                { label: "Minimum pelatihan", value: status.labels_required },
                {
                  label: "Kesiapan",
                  value: status.ready_for_training ? "Siap" : "Belum siap",
                  tone: status.ready_for_training ? "success" : "warning",
                },
              ]}
            />
            <section className="overflow-hidden rounded-xl border bg-card">
              <div className="flex items-center justify-between border-b px-5 py-4">
                <div>
                  <h2 className="font-medium">Distribusi kelas</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Hanya catatan pembayaran benar dan penipuan yang dipakai
                    untuk melatih model.
                  </p>
                </div>
                <StatusBadge
                  kind="profile"
                  value={status.ready_for_training ? "active" : "pending"}
                />
              </div>
              <div className="grid sm:grid-cols-3">
                {Object.entries(status.class_distribution).map(
                  (entry, index) => (
                    <div
                      key={entry[0]}
                      className={
                        index ? "border-t p-5 sm:border-l sm:border-t-0" : "p-5"
                      }
                    >
                      <p className="text-sm capitalize text-muted-foreground">
                        {labelName(entry[0])}
                      </p>
                      <p className="mt-2 text-2xl font-medium">{entry[1]}</p>
                    </div>
                  ),
                )}
              </div>
            </section>
            <p className="text-xs leading-5 text-muted-foreground">
              Pelatihan ditolak bila sampel belum cukup atau hanya terdiri dari
              satu kelas.
            </p>
          </>
        )}
      </DataState>
    </div>
  );
}

function labelName(value: string) {
  return (
    (
      {
        legitimate: "Pembayaran benar",
        fraud: "Penipuan",
        suspicious: "Mencurigakan",
      } as Record<string, string>
    )[value] ?? value
  );
}
