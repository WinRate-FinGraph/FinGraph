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

type Round = {
  round_number: number;
  status: string;
  participant_count: number;
  total_samples: number;
  global_metric_before: number;
  global_metric_after: number;
  raw_data_shared: number;
  participants: { node_name: string; sample_count: number }[];
};
type Status = {
  prototype: boolean;
  aggregation_method: string;
  registered_nodes: number;
  privacy_message: string;
  last_round: Round | null;
};
type Node = {
  id: string;
  node_name: string;
  node_type?: string;
  sample_count: number;
  last_round: number;
  status: string;
};

export default function FederatedPage() {
  const status = useApi<Status>("/federated/status");
  const nodes = useApi<{ items: Node[] }>("/federated/nodes");
  const user = getStoredUser();
  async function run() {
    try {
      await apiFetch("/federated/rounds/run", { method: "POST" });
      toast.success("Putaran pembelajaran bersama selesai");
      await Promise.all([status.reload(), nodes.reload()]);
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "Putaran belum dapat dijalankan",
      );
    }
  }
  const round = status.data?.last_round;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Pembelajaran bersama"
        description="Contoh cara beberapa pihak belajar bersama tanpa mengirim data pembayaran mentah."
        action={
          user?.role === "admin" ? (
            <Button onClick={run}>Jalankan putaran demo</Button>
          ) : undefined
        }
      />
      <DataState
        loading={status.loading || nodes.loading}
        error={status.error || nodes.error}
        onRetry={() => {
          void status.reload();
          void nodes.reload();
        }}
      >
        {status.data && nodes.data && (
          <>
            <section className="rounded-xl border border-warning/25 bg-warning-soft p-5 text-sm leading-6">
              <h2 className="font-medium">Catatan demo</h2>
              <p className="mt-1 text-muted-foreground">Ini masih contoh. Data pembayaran mentah tidak dipindahkan, tetapi perlindungan privasi untuk penggunaan nyata belum diterapkan.</p>
            </section>
            <SummaryStrip
              items={[
                {
                  label: "Node terdaftar",
                  value: status.data.registered_nodes,
                },
                {
                  label: "Metode agregasi",
                  value: status.data.aggregation_method,
                },
                {
                  label: "Putaran terakhir",
                  value: round?.round_number ?? "Belum ada",
                },
                { label: "Data mentah yang dikirim", value: "0" },
              ]}
            />
            {round && (
              <section className="overflow-hidden rounded-xl border bg-card">
                <div className="flex flex-col gap-3 border-b px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="font-medium">
                      Hasil putaran {round.round_number}
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {round.participant_count} partisipan ·{" "}
                      {round.total_samples.toLocaleString("id-ID")} sampel lokal
                    </p>
                  </div>
                  <StatusBadge
                    kind="profile"
                    value={round.status === "completed" ? "active" : "pending"}
                  />
                </div>
                <dl className="grid sm:grid-cols-3">
                  <Metric
                    label="Metrik sebelum"
                    value={formatMetric(round.global_metric_before)}
                  />
                  <Metric
                    label="Metrik sesudah"
                    value={formatMetric(round.global_metric_after)}
                    border
                  />
                  <Metric
                    label="Perubahan"
                    value={`${round.global_metric_after >= round.global_metric_before ? "+" : ""}${((round.global_metric_after - round.global_metric_before) * 100).toFixed(2)} poin`}
                    border
                  />
                </dl>
              </section>
            )}
            <section className="overflow-hidden rounded-xl border bg-card">
              <div className="border-b px-5 py-4">
                <h2 className="font-medium">Node peserta</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Dataset tetap berada pada masing-masing node simulasi.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead className="border-b bg-secondary/60 text-xs text-muted-foreground">
                    <tr>
                      <th className="px-5 py-3.5">Node</th>
                      <th className="px-4 py-3.5">Tipe</th>
                      <th className="px-4 py-3.5 text-right">Sampel lokal</th>
                      <th className="px-4 py-3.5 text-right">Putaran</th>
                      <th className="px-5 py-3.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {nodes.data.items.map((node) => (
                      <tr key={node.id}>
                        <td className="px-5 py-4 font-medium">
                          {node.node_name}
                        </td>
                        <td className="px-4 py-4 text-muted-foreground">
                          {node.node_type ?? "UMKM"}
                        </td>
                        <td className="px-4 py-4 text-right font-technical">
                          {node.sample_count.toLocaleString("id-ID")}
                        </td>
                        <td className="px-4 py-4 text-right font-technical">
                          {node.last_round}
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge kind="profile" value={node.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </DataState>
    </div>
  );
}

function Metric({
  label,
  value,
  border,
}: {
  label: string;
  value: string;
  border?: boolean;
}) {
  return (
    <div className={border ? "border-t p-5 sm:border-l sm:border-t-0" : "p-5"}>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="mt-2 text-xl font-medium">{value}</dd>
    </div>
  );
}
function formatMetric(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
