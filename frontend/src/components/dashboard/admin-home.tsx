"use client";

import Link from "next/link";
import { Activity, ArrowRight, ShieldCheck, Users } from "lucide-react";

import {
  ActivityList,
  ActivityRoleDistribution,
} from "@/components/product/activity";
import {
  DataState,
  EmptyState,
  PageHeader,
  SummaryStrip,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { ActivityMonitoring } from "@/lib/types";

export function AdminHome() {
  const monitoring = useApi<ActivityMonitoring>(
    "/admin/activity-monitoring?period=today&limit=8",
  );
  return (
    <div className="space-y-6">
      <PageHeader
        title="Pusat kendali administrator"
        description="Pantau pengguna, aktivitas sistem, dan kesiapan operasional FinGraph QRIS."
        action={
          <Button asChild>
            <Link href="/dashboard/admin-monitoring">
              Buka monitoring
              <Activity className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        }
      />
      <DataState
        loading={monitoring.loading}
        error={monitoring.error}
        onRetry={monitoring.reload}
      >
        {monitoring.data && (
          <>
            <SummaryStrip
              items={[
                {
                  label: "Pengguna aktif",
                  value: monitoring.data.active_users,
                  hint: `${monitoring.data.active_window_minutes} menit terakhir`,
                  tone: "success",
                },
                {
                  label: "Aktivitas hari ini",
                  value: monitoring.data.activities_today,
                },
                { label: "Total pengguna", value: monitoring.data.total_users },
                {
                  label: "Merchant aktif",
                  value: monitoring.data.active_merchants,
                  tone: "info",
                },
              ]}
            />
            <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr]">
              <section className="overflow-hidden rounded-xl border border-border bg-surface">
                <div className="flex items-center justify-between border-b border-border px-5 py-4">
                  <div>
                    <h2 className="font-medium">Aktivitas terbaru</h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Perubahan nyata yang tercatat di audit log
                    </p>
                  </div>
                  <Link
                    href="/dashboard/audit-logs"
                    className="text-sm font-medium text-primary"
                  >
                    Audit lengkap
                  </Link>
                </div>
                {monitoring.data.recent_activities.length ? (
                  <ActivityList
                    items={monitoring.data.recent_activities}
                    compact
                  />
                ) : (
                  <EmptyState
                    title="Belum ada aktivitas hari ini"
                    description="Login dan tindakan pengguna akan muncul di sini."
                  />
                )}
              </section>
              <div className="space-y-6">
                <section className="rounded-xl border border-border bg-surface p-5">
                  <div className="mb-5 flex items-center gap-3">
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-info-soft text-info">
                      <Users className="h-5 w-5" />
                    </span>
                    <div>
                      <h2 className="font-medium">Aktivitas per role</h2>
                      <p className="text-xs text-muted-foreground">
                        Periode hari ini
                      </p>
                    </div>
                  </div>
                  <ActivityRoleDistribution
                    values={monitoring.data.activity_by_role}
                  />
                </section>
                <section className="rounded-xl border border-success/25 bg-success-soft p-5">
                  <ShieldCheck className="h-5 w-5 text-success" />
                  <h2 className="mt-3 font-medium">Kontrol akses aktif</h2>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    Monitoring ini hanya dapat diakses administrator. Merchant
                    tetap dibatasi ke data usahanya sendiri.
                  </p>
                  <Link
                    href="/dashboard/risk-config"
                    className="mt-4 inline-flex items-center text-sm font-medium text-primary"
                  >
                    Konfigurasi risiko
                    <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Link>
                </section>
              </div>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}
