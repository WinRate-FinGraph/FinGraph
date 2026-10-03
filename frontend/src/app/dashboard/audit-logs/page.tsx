"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";

import {
  ActivityRoleDistribution,
  humanAction,
  humanDescription,
} from "@/components/product/activity";
import { DateRangeSelector } from "@/components/product/interactions";
import {
  DataState,
  EmptyState,
  FilterBar,
  PageHeader,
  PaginationBar,
  SearchInput,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import { jakartaDateKey } from "@/lib/presentation";
import type { ActivityItem, PageResponse } from "@/lib/types";

type AuditPage = PageResponse<ActivityItem> & {
  summary: {
    active_users: number;
    activities_today: number;
    total_users: number;
    active_merchants: number;
  };
  activity_by_role: Record<string, number>;
  top_users: { actor: string; role: string; activity_count: number }[];
};

export default function AuditPage() {
  const [search, setSearch] = useState(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("entity_id") || params.get("search") || "";
  });
  const [period, setPeriod] = useState("30d");
  const [role, setRole] = useState("all");
  const [category, setCategory] = useState("operational");
  const [offset, setOffset] = useState(0);
  const today = jakartaDateKey(new Date());
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      limit: "20",
      offset: String(offset),
      ordering: "newest",
      period,
    });
    if (search.trim()) params.set("search", search.trim());
    if (role !== "all") params.set("role", role);
    params.set("activity_category", category);
    if (period === "custom") {
      params.set("date_from", `${dateFrom}T00:00:00+07:00`);
      params.set("date_to", `${dateTo}T23:59:59+07:00`);
    }
    return `/audit-logs?${params}`;
  }, [category, dateFrom, dateTo, offset, period, role, search]);
  const query = useApi<AuditPage>(path);
  const mostActive = query.data?.top_users[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Riwayat Aktivitas"
        description="Telusuri aktivitas pengguna dan hubungkan setiap keputusan dengan dampak transaksi."
      />
      <FilterBar>
        <SearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
          className="min-w-0 flex-1"
          placeholder="Cari aktor, aksi, atau entitas…"
        />
        <Select
          value={period}
          onValueChange={(value) => {
            setPeriod(value);
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-11 w-full sm:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Hari ini</SelectItem>
            <SelectItem value="7d">7 hari</SelectItem>
            <SelectItem value="30d">30 hari</SelectItem>
            <SelectItem value="custom">Pilih tanggal</SelectItem>
          </SelectContent>
        </Select>
        <Select value={category} onValueChange={(value) => { setCategory(value); setOffset(0); }}>
          <SelectTrigger className="h-11 w-full sm:w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="operational">Operasional</SelectItem>
            <SelectItem value="payment">Pembayaran</SelectItem>
            <SelectItem value="review">Review</SelectItem>
            <SelectItem value="configuration">Konfigurasi</SelectItem>
            <SelectItem value="model">Model & FL</SelectItem>
            <SelectItem value="authentication">Autentikasi</SelectItem>
            <SelectItem value="system">Sistem</SelectItem>
            <SelectItem value="all">Semua kategori</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={role}
          onValueChange={(value) => {
            setRole(value);
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-11 w-full sm:w-40">
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
                  value: query.data.summary.active_users,
                  tone: "success",
                },
                {
                  label: "Aktivitas hari ini",
                  value: query.data.summary.activities_today,
                },
                { label: "Total aktivitas", value: query.data.total },
                {
                  label: "Paling aktif",
                  value: mostActive?.actor.split("@")[0] ?? "—",
                  hint: mostActive
                    ? `${mostActive.activity_count} aktivitas`
                    : undefined,
                  tone: "info",
                },
              ]}
            />
            <div className="grid items-start gap-6 xl:grid-cols-[1fr_280px]">
              <div className="space-y-4">
                {query.data.items.length ? (
                  <div className="overflow-hidden rounded-xl border bg-card">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="border-b bg-secondary/60 text-xs text-muted-foreground">
                          <tr>
                            <th className="px-5 py-3.5">Waktu</th>
                            <th className="px-4 py-3.5">Aktor & role</th>
                            <th className="px-4 py-3.5">Aksi</th>
                            <th className="px-4 py-3.5">Entitas</th>
                            <th className="px-5 py-3.5">Konteks dampak</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {query.data.items.map((item) => (
                            <tr
                              key={item.id}
                              className="align-top hover:bg-secondary/40"
                            >
                              <td className="whitespace-nowrap px-5 py-4 text-xs text-muted-foreground">
                                {formatDateTime(item.created_at)}
                              </td>
                              <td className="px-4 py-4">
                                <p className="font-medium">{item.actor}</p>
                                <StatusBadge
                                  kind="profile"
                                  value={item.actor_role}
                                  className="mt-2"
                                />
                              </td>
                              <td className="px-4 py-4">
                                <p className="font-technical text-xs">
                                  {humanAction(item.action)}
                                </p>
                                <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                                  {humanDescription(item.description) ||
                                    "Aktivitas sistem tercatat."}
                                </p>
                              </td>
                              <td className="px-4 py-4">
                                <p>{item.entity_type}</p>
                                {item.entity_id && (
                                  <p
                                    className="mt-1 max-w-40 truncate font-technical text-[11px] text-muted-foreground"
                                    title={item.entity_id}
                                  >
                                    {item.entity_id}
                                  </p>
                                )}
                              </td>
                              <td className="max-w-sm px-5 py-4">
                                {item.impact ? (
                                  <div>
                                    <p className="font-medium">
                                      {formatCurrency(
                                        item.impact.amount,
                                        item.impact.currency,
                                      )}
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {item.impact.category} · prioritas{" "}
                                      {item.impact.priority}
                                    </p>
                                    <Link
                                      href={`/dashboard/payments/${item.impact.payment_id}`}
                                      className="mt-2 inline-flex items-center text-xs font-medium text-primary"
                                    >
                                      Lihat transaksi
                                      <ArrowRight className="ml-1 h-3.5 w-3.5" />
                                    </Link>
                                  </div>
                                ) : (
                                  <span className="text-xs text-muted-foreground">
                                    Tidak terkait transaksi pembayaran.
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    title="Log tidak ditemukan"
                    description="Ubah periode, role, atau kata kunci pencarian."
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
                <h2 className="font-medium">Distribusi aktivitas</h2>
                <p className="mb-5 mt-1 text-xs text-muted-foreground">
                  Berdasarkan role pelaku saat aksi terjadi
                </p>
                <ActivityRoleDistribution
                  values={query.data.activity_by_role}
                />
              </aside>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}
