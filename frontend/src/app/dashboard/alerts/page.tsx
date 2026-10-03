"use client";

import { useMemo, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { AlertListItem } from "@/components/product/alerts";
import { useSelectedOutlet } from "@/components/providers/outlet-provider";
import {
  DataState,
  EmptyState,
  PageHeader,
  PaginationBar,
  SummaryStrip,
} from "@/components/product/ui";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { AlertItem, PageResponse } from "@/lib/types";

type AlertPage = PageResponse<AlertItem> & {
  status_counts: { open: number; investigating: number; completed: number };
};

export default function AlertsPage() {
  const { selectedId } = useSelectedOutlet();
  const [filter, setFilter] = useState("active");
  const [offset, setOffset] = useState(0);
  const path = useMemo(() => {
    const params = new URLSearchParams({
      limit: "20",
      offset: String(offset),
      status: filter,
    });
    if (selectedId !== "all") params.set("outlet_id", selectedId);
    return `/alerts?${params}`;
  }, [filter, offset, selectedId]);
  const query = useApi<AlertPage>(path);
  async function update(id: string, status: string) {
    try {
      await apiFetch(`/alerts/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      toast.success(
        status === "resolved"
          ? "Pemeriksaan diselesaikan"
          : "Peringatan ditandai sedang diperiksa",
      );
      await query.reload();
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "Status belum dapat diperbarui",
      );
    }
  }
  const counts = query.data?.status_counts;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Peringatan"
        description="Tinjau pembayaran yang membutuhkan konfirmasi sebelum pesanan diserahkan."
      />
      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {query.data && (
          <>
            <SummaryStrip
              items={[
                {
                  label: "Butuh tindakan",
                  value: counts?.open ?? 0,
                  tone: "danger",
                },
                {
                  label: "Sedang diperiksa",
                  value: counts?.investigating ?? 0,
                  tone: "warning",
                },
                {
                  label: "Selesai",
                  value: counts?.completed ?? 0,
                  tone: "success",
                },
              ]}
            />
            <Tabs
              value={filter}
              onValueChange={(value) => {
                setFilter(value);
                setOffset(0);
              }}
            >
              <TabsList className="w-fit max-w-full justify-start rounded-xl bg-secondary p-1">
                <TabsTrigger value="active">Aktif</TabsTrigger>
                <TabsTrigger value="open">Butuh tindakan</TabsTrigger>
                <TabsTrigger value="investigating">
                  Sedang diperiksa
                </TabsTrigger>
                <TabsTrigger value="completed">Selesai</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
              <div className="space-y-4">
                {query.data.items.length ? (
                  <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface">
                    {query.data.items.map((alert) => (
                      <AlertListItem
                        key={alert.id}
                        alert={alert}
                        onStart={(id) => update(id, "investigating")}
                        onResolve={(id) => {
                          void update(id, "resolved");
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={CheckCircle2}
                    title="Tidak ada peringatan pada filter ini"
                    description="Pembayaran yang membutuhkan tindakan akan muncul di sini."
                  />
                )}
                <PaginationBar
                  total={query.data.total}
                  limit={query.data.limit}
                  offset={query.data.offset}
                  onPageChange={setOffset}
                />
              </div>
              <aside className="rounded-xl border border-border bg-surface p-5">
                <h2 className="font-medium">Sebelum menyerahkan pesanan</h2>
                <ol className="mt-4 space-y-3 text-sm leading-6 text-muted-foreground">
                  <li>1. Cocokkan nominal dengan total pesanan.</li>
                  <li>2. Pastikan konfirmasi penyedia sudah diterima.</li>
                  <li>3. Tahan pesanan jika masih ada perbedaan.</li>
                </ol>
              </aside>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}
