"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw, UserCheck } from "lucide-react";

import {
  ActivityList,
  ActivityRoleDistribution,
} from "@/components/product/activity";
import { DateRangeSelector } from "@/components/product/interactions";
import {
  DataState,
  EmptyState,
  FilterBar,
  PageHeader,
  SummaryStrip,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { jakartaDateKey } from "@/lib/presentation";
import type { ActivityMonitoring } from "@/lib/types";

export default function AdminMonitoringPage() {
  const [period, setPeriod] = useState("today");
  const [role, setRole] = useState("all");
  const [category, setCategory] = useState("operational");
  const today = jakartaDateKey(new Date());
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const path = useMemo(() => {
    const params = new URLSearchParams({ period, limit: "20" });
    if (role !== "all") params.set("role", role);
    params.set("activity_category", category);
    if (period === "custom") {
      params.set("date_from", `${dateFrom}T00:00:00+07:00`);
      params.set("date_to", `${dateTo}T23:59:59+07:00`);
    }
    return `/admin/activity-monitoring?${params}`;
  }, [category, dateFrom, dateTo, period, role]);
  const query = useApi<ActivityMonitoring>(path);
  const reload = query.reload;

  useEffect(() => {
    const timer = window.setInterval(() => {
      void reload();
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [reload]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitoring Aktivitas"
        description="Pantau pengguna aktif dan tindakan terbaru dari data audit sistem."
        action={
          <Button variant="outline" onClick={() => void query.reload()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Muat ulang
          </Button>
        }
      />
      <FilterBar>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="h-11 w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Hari ini</SelectItem>
            <SelectItem value="7d">7 hari</SelectItem>
            <SelectItem value="30d">30 hari</SelectItem>
            <SelectItem value="custom">Pilih tanggal</SelectItem>
          </SelectContent>
        </Select>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="h-11 w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua role</SelectItem>
            <SelectItem value="merchant">Merchant</SelectItem>
            <SelectItem value="analyst">Analyst</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="system">Sistem</SelectItem>
          </SelectContent>
        </Select>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="h-11 w-full sm:w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="operational">Operasional</SelectItem>
            <SelectItem value="payment">Pembayaran</SelectItem>
            <SelectItem value="review">Review</SelectItem>
            <SelectItem value="configuration">Konfigurasi</SelectItem>
            <SelectItem value="model">Model & FL</SelectItem>
            <SelectItem value="authentication">Autentikasi</SelectItem>
            <SelectItem value="all">Semua kategori</SelectItem>
          </SelectContent>
        </Select>
        {period === "custom" && (
          <DateRangeSelector
            start={dateFrom}
            end={dateTo}
            max={today}
            onStartChange={setDateFrom}
            onEndChange={setDateTo}
          />
        )}
        <p className="ml-auto text-xs text-muted-foreground">
          Diperbarui otomatis setiap 30 detik
        </p>
      </FilterBar>
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
                  label: "Pengguna aktif",
                  value: query.data.active_users,
                  hint: `${query.data.active_window_minutes} menit terakhir`,
                  tone: "success",
                },
                {
                  label: "Aktivitas hari ini",
                  value: query.data.activities_today,
                },
                { label: "Total pengguna", value: query.data.total_users },
                {
                  label: "Merchant aktif",
                  value: query.data.active_merchants,
                  tone: "info",
                },
              ]}
            />
            <div className="grid items-start gap-6 xl:grid-cols-[1.35fr_.65fr]">
              <section className="overflow-hidden rounded-xl border border-border bg-surface">
                <div className="border-b border-border px-5 py-4">
                  <h2 className="font-medium">Aktivitas terbaru</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Data langsung dari riwayat sistem, bukan tampilan statis.
                  </p>
                </div>
                {query.data.recent_activities.length ? (
                  <ActivityList items={query.data.recent_activities} />
                ) : (
                  <EmptyState
                    icon={Activity}
                    title="Belum ada aktivitas"
                    description="Ubah periode atau role untuk melihat aktivitas lain."
                  />
                )}
              </section>
              <div className="space-y-6">
                <section className="rounded-xl border border-border bg-surface p-5">
                  <h2 className="font-medium">Distribusi per role</h2>
                  <p className="mb-5 mt-1 text-xs text-muted-foreground">
                    Aktivitas pada periode terpilih
                  </p>
                  <ActivityRoleDistribution
                    values={query.data.activity_by_role}
                  />
                </section>
                <section className="rounded-xl border border-border bg-surface p-5">
                  <div className="flex items-center gap-3">
                    <UserCheck className="h-5 w-5 text-primary" />
                    <h2 className="font-medium">Pengguna paling aktif</h2>
                  </div>
                  <div className="mt-4 divide-y divide-border">
                    {query.data.top_users.map((item) => (
                      <div
                        key={`${item.actor}-${item.role}`}
                        className="flex items-center justify-between gap-4 py-3"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">
                            {item.actor}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {item.role}
                          </p>
                        </div>
                        <strong className="font-technical text-xs">
                          {item.activity_count}
                        </strong>
                      </div>
                    ))}
                    {!query.data.top_users.length && (
                      <p className="py-4 text-sm text-muted-foreground">
                        Belum ada aktivitas pengguna.
                      </p>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}
