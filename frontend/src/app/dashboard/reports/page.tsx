"use client";

import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DateRangeSelector } from "@/components/product/interactions";
import { PaymentTable } from "@/components/product/payments";
import {
  ChartCard,
  DataState,
  FilterBar,
  PageHeader,
  PaginationBar,
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
import { formatCurrency, formatShortDate } from "@/lib/format";
import { jakartaDateKey } from "@/lib/presentation";
import type { ImpactDashboard, Payment } from "@/lib/types";

export default function ReportsPage() {
  const [period, setPeriod] = useState("30d");
  const [priority, setPriority] = useState("all");
  const [offset, setOffset] = useState(0);
  const today = jakartaDateKey(new Date());
  const [dateFrom, setDateFrom] = useState(shiftedDateKey(-29));
  const [dateTo, setDateTo] = useState(today);
  const { selectedId } = useSelectedOutlet();
  const path = useMemo(() => {
    const params = new URLSearchParams({
      period,
      limit: "20",
      offset: String(offset),
    });
    if (selectedId !== "all") params.set("outlet_id", selectedId);
    if (priority !== "all") params.set("priority", priority);
    if (period === "custom") {
      params.set("date_from", dateFrom);
      params.set("date_to", dateTo);
    }
    return `/reports/impact-dashboard?${params}`;
  }, [dateFrom, dateTo, offset, period, priority, selectedId]);
  const query = useApi<ImpactDashboard>(path);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Laporan Dampak Usaha"
        description="Lihat kondisi pembayaran, dampak risiko, dan tindakan yang disarankan dari agregasi database."
        action={
          <Button
            variant="outline"
            disabled={!query.data?.items.length}
            onClick={() => query.data && exportCsv(query.data.items)}
          >
            <Download className="mr-2 h-4 w-4" />
            Unduh halaman CSV
          </Button>
        }
      />
      <FilterBar>
        <Select
          value={period}
          onValueChange={(value) => {
            setPeriod(value);
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-11 w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">7 hari</SelectItem>
            <SelectItem value="30d">30 hari</SelectItem>
            <SelectItem value="month">Bulan ini</SelectItem>
            <SelectItem value="custom">Pilih tanggal</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={priority}
          onValueChange={(value) => {
            setPriority(value);
            setOffset(0);
          }}
        >
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
        {period === "custom" && (
          <DateRangeSelector
            start={dateFrom}
            end={dateTo}
            max={today}
            onStartChange={(value) => {
              setDateFrom(value);
              setOffset(0);
            }}
            onEndChange={(value) => {
              setDateTo(value);
              setOffset(0);
            }}
          />
        )}
        <p className="ml-auto text-xs text-muted-foreground">
          Filter outlet mengikuti pilihan di bagian atas.
        </p>
      </FilterBar>
      <DataState
        loading={query.loading}
        error={query.error}
        empty={Boolean(query.data && !query.data.metrics.payment_count)}
        emptyTitle="Belum ada pembayaran pada filter ini"
        emptyDescription="Pilih periode, outlet, atau prioritas lain."
        onRetry={query.reload}
      >
        {query.data && query.data.metrics.payment_count > 0 && (
          <>
            <SummaryStrip
              items={[
                {
                  label: "Total pembayaran",
                  value: query.data.metrics.payment_count,
                },
                {
                  label: "Nilai transaksi",
                  value: formatCurrency(query.data.metrics.transaction_value),
                  tone: "success",
                },
                {
                  label: "Pembayaran berhasil dan berisiko rendah",
                  value: `${query.data.metrics.verified_percent}%`,
                  tone: "success",
                },
                {
                  label: "Perlu tindakan",
                  value:
                    query.data.metrics.review_count +
                    query.data.metrics.held_count,
                  tone: "warning",
                },
              ]}
            />
            <div className="grid gap-6 lg:grid-cols-2">
              <VolumeChart data={query.data} />
              <PriorityChart data={query.data} />
            </div>
            <section className="rounded-xl border border-border bg-surface p-5">
              <h2 className="font-medium">Insight dan rekomendasi</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <Insight
                  label="Outlet volume tertinggi"
                  value={query.data.insights.top_outlet ?? "Belum ada"}
                />
                <Insight
                  label="Alert terselesaikan"
                  value={String(query.data.insights.resolved_alerts)}
                />
                <Insight
                  label="Disarankan ditahan"
                  value={formatCurrency(
                    query.data.metrics.recommended_hold_value,
                  )}
                />
                <Insight
                  label="Tindakan"
                  value={
                    query.data.metrics.held_count
                      ? "Tinjau prioritas tinggi"
                      : query.data.metrics.review_count
                        ? "Verifikasi pembayaran"
                        : "Lanjutkan pemantauan"
                  }
                />
              </div>
            </section>
            <section className="space-y-4">
              <div>
              <h2 className="font-medium">Detail dampak dan riwayat tindakan</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Kategori dan prioritas ditampilkan eksplisit; setiap baris
                  dapat ditinjau atau dibuka riwayat aksinya.
                </p>
              </div>
              <PaymentTable items={query.data.items} />
              <PaginationBar
                total={query.data.total}
                limit={query.data.limit}
                offset={query.data.offset}
                onPageChange={setOffset}
              />
            </section>
            <p className="text-xs text-muted-foreground">
              Estimasi nominal transaksi berisiko yang disarankan ditahan bukan
              dana yang dikendalikan oleh FinGraph.
            </p>
          </>
        )}
      </DataState>
    </div>
  );
}

function VolumeChart({ data }: { data: ImpactDashboard }) {
  const values = data.timeline.map((item) => ({
    label: formatShortDate(`${item.date}T12:00:00Z`),
    value: item.transaction_value,
  }));
  const max = Math.max(...values.map((item) => item.value), 1);
  return (
    <ChartCard
      title="Nilai transaksi per hari"
      description="Agregasi server-side pada periode pilihan"
      summary={`Nilai harian tertinggi ${formatCurrency(max)}.`}
    >
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={values}
            margin={{ top: 12, right: 8, left: -14, bottom: 0 }}
          >
            <defs>
              <linearGradient id="impactReportArea" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--primary)"
                  stopOpacity={0.28}
                />
                <stop
                  offset="100%"
                  stopColor="var(--primary)"
                  stopOpacity={0.02}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              vertical={false}
              stroke="var(--border)"
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              minTickGap={22}
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              tickFormatter={(value) => String(value).split(" ")[0]}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={55}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              tickFormatter={compactRupiah}
            />
            <Tooltip
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
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--primary)"
              strokeWidth={2}
              fill="url(#impactReportArea)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

function PriorityChart({ data }: { data: ImpactDashboard }) {
  const values = [
    {
      key: "rendah",
      label: "Rendah",
      value: data.priority_distribution.rendah,
      color: "bg-success",
    },
    {
      key: "sedang",
      label: "Sedang",
      value: data.priority_distribution.sedang,
      color: "bg-warning",
    },
    {
      key: "tinggi",
      label: "Tinggi",
      value: data.priority_distribution.tinggi,
      color: "bg-danger",
    },
  ];
  const max = Math.max(...values.map((item) => item.value), 1);
  return (
    <ChartCard
      title="Komposisi prioritas"
      description="Prioritas eksplisit hasil pemetaan risiko"
      summary={`${values[0].value} rendah, ${values[1].value} sedang, ${values[2].value} tinggi.`}
    >
      <div className="space-y-6 py-3">
        {values.map((item) => (
          <div key={item.key}>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium">Prioritas {item.label}</span>
              <span className="font-technical text-xs">{item.value}</span>
            </div>
            <div className="h-3 rounded-full bg-surface-subtle">
              <div
                className={`h-full rounded-full ${item.color}`}
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

function Insight({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-subtle p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-sm font-medium">{value}</p>
    </div>
  );
}
function compactRupiah(value: number) {
  return value >= 1_000_000
    ? `${Math.round(value / 1_000_000)}jt`
    : value >= 1_000
      ? `${Math.round(value / 1_000)}rb`
      : String(value);
}
function shiftedDateKey(days: number) {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + days);
  return jakartaDateKey(value);
}
function exportCsv(items: Payment[]) {
  const rows = [
    ["Referensi", "Waktu", "Kategori", "Prioritas", "Nominal", "Status"],
    ...items.map((item) => [
      item.provider_reference,
      item.transaction_time,
      item.category,
      item.priority,
      item.amount,
      item.payment_status,
    ]),
  ];
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "fingraph-qris-impact.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}
function csvCell(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}
