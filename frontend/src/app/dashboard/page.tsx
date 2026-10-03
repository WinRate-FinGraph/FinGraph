"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  CalendarDays,
  Plus,
  QrCode,
  ShieldCheck,
  Store,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PaymentListItem } from "@/components/product/payments";
import { AlertListItem } from "@/components/product/alerts";
import {
  ChartCard,
  DataState,
  DemoModeBanner,
  FilterBar,
  PageHeader,
  StatusBadge,
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
import { useSelectedOutlet } from "@/components/providers/outlet-provider";
import { useApi } from "@/hooks/use-api";
import {
  formatCurrency,
  formatDateTime,
  formatShortDate,
  greetingForJakarta,
} from "@/lib/format";
import { getStoredUser } from "@/lib/auth";
import { dashboardHomeForRole } from "@/lib/access";
import type { AlertItem, MerchantDashboard, PageResponse } from "@/lib/types";
import { AdminHome } from "@/components/dashboard/admin-home";
import { useSubscription } from "@/components/providers/subscription-provider";
import { planAtLeast } from "@/lib/plans";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

type AnalystDashboard = {
  total_payments: number;
  total_merchants: number;
  total_orders: number;
  open_alerts: number;
  high_risk_payments: number;
  average_fraud_score: number;
  risk_distribution: Record<string, number>;
};

export default function DashboardPage() {
  const user = getStoredUser();
  const home = dashboardHomeForRole(user?.role);
  return home === "merchant-home" ? (
    <MerchantHome />
  ) : home === "admin-home" ? (
    <AdminHome />
  ) : (
    <AnalystHome />
  );
}

function MerchantHome() {
  const { plan } = useSubscription();
  // Dataset demo bersifat deterministik dan mencakup beberapa hari; 30 hari
  // memberi ringkasan bermakna saat akun pertama kali dibuka.
  const [period, setPeriod] = useState("30d");
  const [priority, setPriority] = useState("all");
  const { selectedId, selectedName } = useSelectedOutlet();
  const path = useMemo(() => {
    const params = new URLSearchParams({ period });
    if (selectedId !== "all") params.set("outlet_id", selectedId);
    if (priority !== "all") params.set("priority", priority);
    return `/merchants/dashboard?${params}`;
  }, [period, priority, selectedId]);
  const dashboard = useApi<MerchantDashboard>(path);
  const data = dashboard.data;
  const impact = data?.impact;
  const actionPayments = impact?.risk_items ?? [];
  const outlet = selectedName ?? data?.qris_status[0]?.outlet ?? "semua outlet";
  return (
    <div className="space-y-7">
      <DemoModeBanner />
      <PageHeader
        title={
          data
            ? `${greetingForJakarta()}, ${firstName(data.merchant.owner_name)}`
            : `${greetingForJakarta()}`
        }
        description={`Berikut kondisi pembayaran ${outlet} untuk ${periodLabel(period).toLowerCase()}.`}
      />
      <FilterBar>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="h-11 w-full sm:w-44">
            <CalendarDays className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Hari ini</SelectItem>
            <SelectItem value="7d">7 hari</SelectItem>
            <SelectItem value="30d">30 hari</SelectItem>
            <SelectItem value="month">Bulan ini</SelectItem>
          </SelectContent>
        </Select>
        {planAtLeast(plan, "growth") && (
          <Select value={priority} onValueChange={setPriority}>
            <SelectTrigger className="h-11 w-full sm:w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua prioritas</SelectItem>
              <SelectItem value="rendah">Prioritas rendah</SelectItem>
              <SelectItem value="sedang">Prioritas sedang</SelectItem>
              <SelectItem value="tinggi">Prioritas tinggi</SelectItem>
            </SelectContent>
          </Select>
        )}
        <p className="text-xs text-muted-foreground sm:ml-auto">
          Outlet dipilih dari bagian atas halaman.
        </p>
      </FilterBar>
      <DataState
        loading={dashboard.loading}
        error={dashboard.error}
        onRetry={dashboard.reload}
      >
        {data && impact && (
          <>
            <section
              className={
                actionPayments.length
                  ? "rounded-xl border border-warning/25 bg-warning-soft px-5 py-4"
                  : "rounded-xl border border-success/25 bg-success-soft px-5 py-4"
              }
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3.5">
                  {actionPayments.length ? (
                    <AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-warning" />
                  ) : (
                    <ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-success" />
                  )}
                  <div>
                    <h2 className="text-lg font-medium tracking-[-.02em]">
                      {actionPayments.length
                        ? `${actionPayments.length} pembayaran aktif perlu tindakan`
                        : "Tidak ada pembayaran yang perlu diperiksa"}
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {actionPayments.length
                        ? `${formatCurrency(actionPayments.reduce((sum, item) => sum + item.amount, 0))} perlu ditinjau sebelum pesanan diserahkan.`
                        : "Ini bukan jaminan semua pembayaran aman; tidak ada yang perlu diperiksa pada filter ini."}
                    </p>
                  </div>
                </div>
                <Button asChild className="shrink-0">
                  <Link
                    href={
                      actionPayments.length
                        ? "/dashboard/alerts"
                        : "/dashboard/payments"
                    }
                  >
                    {actionPayments.length
                      ? "Tinjau sekarang"
                      : "Lihat pembayaran"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </section>
            <SummaryStrip
              items={[
                {
                  label: "Nilai pembayaran",
                  value: formatCurrency(impact.metrics.transaction_value),
                  hint: periodLabel(period),
                  tone: "success",
                },
                {
                  label: "Pembayaran berhasil",
                  value: impact.metrics.successful_count,
                  hint: `${impact.metrics.payment_count} pembayaran terfilter`,
                },
                {
                  label: "Perlu diperiksa",
                  value: impact.metrics.review_count,
                  tone: "warning",
                },
                {
                  label: "Disarankan ditahan",
                  value: impact.metrics.held_count,
                  tone: "danger",
                },
              ]}
            />
            <section className="rounded-xl border bg-card px-5 py-4 text-sm">
              <div className="grid gap-2 text-muted-foreground sm:grid-cols-3">
                <p><span className="font-medium text-foreground">Sumber:</span> database demo dan simulator pembayaran</p>
                <p><span className="font-medium text-foreground">Periode:</span> {formatDateTime(impact.window.start)} – {formatDateTime(impact.window.end)}</p>
                <p><span className="font-medium text-foreground">Pembayaran terbaru:</span> {impact.items[0] ? formatDateTime(impact.items[0].transaction_time) : "Belum ada"}</p>
              </div>
            </section>
            <section>
              <h2 className="mb-3 text-sm font-medium">Tindakan cepat</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                <QuickAction
                  href="/dashboard/payments/check"
                  icon={QrCode}
                  title="Cek pembayaran"
                  detail="Pastikan dana benar-benar masuk"
                  primary
                />
                <QuickAction
                  href="/dashboard/orders"
                  icon={Plus}
                  title="Buat pesanan"
                  detail="Catat nominal sebelum dibayar"
                />
                <QuickAction
                  href="/dashboard/qris"
                  icon={Store}
                  title="Lihat QRIS"
                  detail="Periksa profil outlet"
                />
              </div>
            </section>
            <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
              <section className="overflow-hidden rounded-xl border border-border bg-surface">
                <div className="flex items-center justify-between border-b border-border px-5 py-4">
                  <div>
                    <h2 className="font-medium">Pembayaran terbaru</h2>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {planAtLeast(plan, "growth")
                        ? "Sesuai filter periode, outlet, dan prioritas"
                        : "Sesuai periode yang dipilih"}
                    </p>
                  </div>
                  <Link
                    href="/dashboard/payments"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Lihat semua
                  </Link>
                </div>
                <div className="divide-y divide-border">
                  {impact.items.slice(0, 5).map((item) => (
                    <PaymentListItem
                      key={item.id}
                      item={item}
                      compact
                      showGrowthFeatures={planAtLeast(plan, "growth")}
                    />
                  ))}
                </div>
              </section>
              <BusinessChart
                timeline={impact.timeline}
                verifiedPercent={impact.metrics.verified_percent}
              />
            </div>
            <section className="flex flex-col gap-4 rounded-xl border border-border bg-surface px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-success-soft text-success">
                  <QrCode className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-medium">
                    QRIS {data.qris_status[0]?.outlet ?? "usaha"}
                  </p>
                  <p className="mt-0.5 font-technical text-xs text-muted-foreground">
                    {data.qris_status[0]?.nmid ?? "Profil belum tersedia"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge
                  kind="profile"
                  value={data.qris_status[0]?.status ?? "pending"}
                />
                <Link
                  href="/dashboard/qris"
                  className="text-sm font-medium text-primary"
                >
                  Kelola
                </Link>
              </div>
            </section>
          </>
        )}
      </DataState>
    </div>
  );
}

function QuickAction({
  href,
  icon: Icon,
  title,
  detail,
  primary,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  detail: string;
  primary?: boolean;
}) {
  return (
    <Link
      href={href}
      className={
        primary
          ? "group flex min-h-[92px] items-center gap-3.5 rounded-xl bg-primary px-5 text-primary-foreground shadow-sm transition hover:bg-primary-hover"
          : "group flex min-h-[92px] items-center gap-3.5 rounded-xl border border-border bg-surface px-5 transition hover:border-border-strong hover:bg-surface-subtle"
      }
    >
      <span
        className={
          primary
            ? "grid h-10 w-10 place-items-center rounded-xl bg-surface/15"
            : "grid h-10 w-10 place-items-center rounded-xl bg-surface-subtle text-primary"
        }
      >
        <Icon className="h-[18px] w-[18px]" />
      </span>
      <span>
        <span className="block font-medium">{title}</span>
        <span
          className={
            primary
              ? "mt-1 block text-xs opacity-75"
              : "mt-1 block text-xs text-muted-foreground"
          }
        >
          {detail}
        </span>
      </span>
    </Link>
  );
}

function BusinessChart({
  timeline,
  verifiedPercent,
}: {
  timeline: { date: string; transaction_value: number }[];
  verifiedPercent: number;
}) {
  const days = timeline.map((item) => ({
    label: formatShortDate(`${item.date}T12:00:00Z`),
    value: item.transaction_value,
  }));
  const max = Math.max(...days.map((day) => day.value), 1);
  return (
    <ChartCard
      title="Perkembangan pembayaran"
      description={`${verifiedPercent}% pembayaran berhasil dan berisiko rendah`}
      summary={`Nilai pembayaran tertinggi pada periode pilihan adalah ${formatCurrency(max)}.`}
      className="flex h-full min-h-[520px] flex-col"
      contentClassName="min-h-[350px] flex-1"
    >
      {days.length > 1 ? (
        <div className="h-full min-h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={days}
              margin={{ top: 12, right: 4, left: -18, bottom: 0 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="var(--border)"
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickFormatter={(value) => String(value).split(" ")[0]}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={52}
                scale="sqrt"
                domain={[0, "dataMax"]}
                tick={{ fill: "var(--muted)", fontSize: 10 }}
                tickFormatter={(value) =>
                  value >= 1_000_000
                    ? `${Math.round(value / 1_000_000)}jt`
                    : value >= 1_000
                      ? `${Math.round(value / 1_000)}rb`
                      : String(value)
                }
              />
              <Tooltip
                cursor={{ fill: "var(--surface-subtle)" }}
                contentStyle={{
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  color: "var(--foreground)",
                  fontSize: 12,
                }}
                formatter={(value) => [
                  formatCurrency(Number(value)),
                  "Nilai transaksi",
                ]}
              />
              <Bar
                dataKey="value"
                fill="var(--primary)"
                radius={[6, 6, 0, 0]}
                minPointSize={5}
                maxBarSize={34}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="grid h-full min-h-[350px] place-items-center text-center text-sm text-muted-foreground">
          {days.length === 1 ? `Satu titik data tersedia: ${formatCurrency(days[0].value)}. Perlu lebih dari satu hari untuk melihat tren.` : "Belum ada pembayaran pada filter ini."}
        </div>
      )}
    </ChartCard>
  );
}

function AnalystHome() {
  const summary = useApi<AnalystDashboard>("/dashboard/summary");
  const alerts = useApi<PageResponse<AlertItem>>("/alerts?status=active&limit=8");
  async function updateAlert(id: string, status: string) {
    try {
      await apiFetch(`/alerts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
      await alerts.reload();
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "Status belum diperbarui");
    }
  }
  return (
    <div className="space-y-6">
      <PageHeader
        title="Ringkasan operasional"
        description="Pantau pembayaran, peringatan, dan pemeriksaan yang perlu dilakukan."
        action={
          <Button asChild>
            <Link href="/dashboard/payments">Buka pembayaran</Link>
          </Button>
        }
      />
      <DataState
        loading={summary.loading || alerts.loading}
        error={summary.error || alerts.error}
        onRetry={() => {
          void summary.reload();
          void alerts.reload();
        }}
      >
        {summary.data && alerts.data && (
          <>
            <SummaryStrip
              items={[
                { label: "Pembayaran", value: summary.data.total_payments },
                {
                  label: "Merchant aktif",
                  value: summary.data.total_merchants,
                },
                {
                  label: "Alert terbuka",
                  value: summary.data.open_alerts,
                  tone: "warning",
                },
                {
                  label: "Risiko tinggi",
                  value: summary.data.high_risk_payments,
                  tone: "danger",
                },
              ]}
            />
            <div className="grid gap-6 xl:grid-cols-[1.3fr_.7fr]">
              <section className="overflow-hidden rounded-xl border border-border bg-surface">
                <div className="flex items-center justify-between border-b border-border px-5 py-4">
                  <h2 className="font-medium">Antrean review aktif</h2>
                  <Link
                    href="/dashboard/alerts"
                    className="text-sm font-medium text-primary"
                  >
                    Lihat semua
                  </Link>
                </div>
                <div className="divide-y divide-border">
                  {alerts.data.items.slice(0, 6).map((alert) => (
                    <AlertListItem key={alert.id} alert={alert} onStart={(id) => updateAlert(id, "investigating")} onResolve={(id) => { void updateAlert(id, "resolved"); }} />
                  ))}
                  {!alerts.data.items.length && <p className="p-6 text-sm text-muted-foreground">Tidak ada alert aktif pada saat ini.</p>}
                </div>
              </section>
              <section className="rounded-xl border border-border bg-surface p-5">
                <div className="flex items-center gap-3 border-b border-border pb-4">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-accent-foreground">
                    <BrainCircuit className="h-5 w-5" />
                  </span>
                  <div>
                    <h2 className="font-medium">Analisis FinGraph</h2>
                    <p className="text-xs text-muted-foreground">
                      Ringkasan skor pada data aktif
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 border-b border-border py-4">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Rata-rata risiko
                    </p>
                    <p className="mt-1 text-2xl font-medium tracking-[-.035em]">
                      {Math.round(summary.data.average_fraud_score * 100)}
                      <span className="text-xs font-normal text-muted-foreground">
                        /100
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Alert terbuka</p>
                    <p className="mt-1 text-2xl font-medium tracking-[-.035em]">
                      {summary.data.open_alerts}
                    </p>
                  </div>
                </div>
                <h3 className="mt-4 text-sm font-medium">
                  Distribusi keputusan
                </h3>
                <div className="mt-4 space-y-5">
                  {(["low", "medium", "high"] as const).map((level) => {
                    const value = summary.data!.risk_distribution[level] ?? 0;
                    const max = Math.max(summary.data!.total_payments, 1);
                    return (
                      <div key={level}>
                        <div className="mb-2 flex items-center justify-between">
                          <StatusBadge value={level} />
                          <span className="font-technical text-xs">
                            {value}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-surface-subtle">
                          <div
                            className={
                              level === "low"
                                ? "h-full rounded-full bg-success"
                                : level === "medium"
                                  ? "h-full rounded-full bg-warning"
                                  : "h-full rounded-full bg-danger"
                            }
                            style={{ width: `${(value / max) * 100}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}

function firstName(value: string) {
  return value.trim().split(/\s+/)[0] || value;
}
function periodLabel(value: string) {
  return value === "today"
    ? "Hari ini"
    : value === "7d"
      ? "7 hari"
      : value === "30d"
        ? "30 hari"
        : "Bulan ini";
}
