"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CalendarDays, QrCode } from "lucide-react";
import { PaymentTable } from "@/components/product/payments";
import { useSelectedOutlet } from "@/components/providers/outlet-provider";
import {
  DataState,
  EmptyState,
  FilterBar,
  PageHeader,
  PaginationBar,
  SearchInput,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { getStoredUser } from "@/lib/auth";
import type { PageResponse, Payment } from "@/lib/types";
import { useSubscription } from "@/components/providers/subscription-provider";
import { planAtLeast } from "@/lib/plans";

const PAGE_SIZE = 20;
const filters = [
  { value: "all", label: "Semua" },
  { value: "low", label: "Risiko rendah" },
  { value: "medium", label: "Perlu diperiksa" },
  { value: "high", label: "Berisiko" },
];

export default function PaymentsPage() {
  const user = getStoredUser();
  const analyst = user?.role !== "merchant";
  const { plan } = useSubscription();
  const showGrowthFeatures = analyst || planAtLeast(plan, "growth");
  const selectedOutlet = useSelectedOutlet();
  const [risk, setRisk] = useState("all");
  const [search, setSearch] = useState("");
  const [outlet, setOutlet] = useState("all");
  const [period, setPeriod] = useState("30");
  const [priority, setPriority] = useState("all");
  const [offset, setOffset] = useState(0);
  const effectiveOutlet = outlet !== "all" ? outlet : selectedOutlet.selectedId;
  const path = useMemo(() => {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
      ordering: analyst ? "risk_desc" : "newest",
    });
    if (risk !== "all") params.set("risk_level", risk);
    if (showGrowthFeatures && priority !== "all") params.set("priority", priority);
    if (search.trim()) params.set("search", search.trim());
    if (!analyst && effectiveOutlet !== "all")
      params.set("outlet_id", effectiveOutlet);
    const from = new Date();
    from.setDate(from.getDate() - Number(period));
    params.set("date_from", from.toISOString());
    return `/payments?${params}`;
  }, [analyst, effectiveOutlet, offset, period, priority, risk, search, showGrowthFeatures]);
  const query = useApi<PageResponse<Payment>>(path);

  return (
    <div className="space-y-6">
      <PageHeader
        title={analyst ? "Investigasi pembayaran" : "Pembayaran"}
        description={
          analyst
            ? "Cari pembayaran yang perlu diperiksa."
            : "Lihat pembayaran masuk dan tindakan yang perlu dilakukan."
        }
        action={
          <Button asChild>
            <Link href="/dashboard/payments/check">
              <QrCode className="mr-2 h-4 w-4" />
              Cek Pembayaran
            </Link>
          </Button>
        }
      />
      <Tabs
        value={risk}
        onValueChange={(value) => {
          setRisk(value);
          setOffset(0);
        }}
      >
        <TabsList className="w-fit max-w-full justify-start rounded-xl bg-secondary p-1">
          {filters.map((item) => (
            <TabsTrigger
              key={item.value}
              value={item.value}
              className="whitespace-nowrap"
            >
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <FilterBar>
        <SearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
          className="flex-1"
          placeholder="Cari referensi atau pesanan…"
        />
        <Select
          value={period}
          onValueChange={(value) => {
            setPeriod(value);
            setOffset(0);
          }}
        >
          <SelectTrigger className="h-11 w-full bg-card sm:w-40">
            <CalendarDays className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">7 hari</SelectItem>
            <SelectItem value="30">30 hari</SelectItem>
            <SelectItem value="90">90 hari</SelectItem>
          </SelectContent>
        </Select>
        {showGrowthFeatures && (
          <Select
            value={priority}
            onValueChange={(value) => {
              setPriority(value);
              setOffset(0);
            }}
          >
            <SelectTrigger className="h-11 w-full bg-card sm:w-44">
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
        {!analyst && showGrowthFeatures && (
          <Select
            value={outlet}
            onValueChange={(value) => {
              setOutlet(value);
              setOffset(0);
            }}
          >
            <SelectTrigger className="h-11 w-full bg-card sm:w-48">
              <SelectValue placeholder="Semua outlet" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua outlet</SelectItem>
              {selectedOutlet.outlets.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FilterBar>
      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {query.data &&
          (query.data.items.length ? (
            <>
              <p className="text-sm text-muted-foreground">
                Menampilkan{" "}
                <strong className="text-foreground">
                  {query.data.offset + 1}–
                  {Math.min(
                    query.data.offset + query.data.limit,
                    query.data.total,
                  )}
                </strong>{" "}
                dari {query.data.total} pembayaran
              </p>
              <PaymentTable items={query.data.items} analyst={analyst} />
              <PaginationBar
                total={query.data.total}
                limit={query.data.limit}
                offset={query.data.offset}
                onPageChange={setOffset}
              />
            </>
          ) : (
            <EmptyState
              title="Pembayaran tidak ditemukan"
              description="Coba ubah kata kunci, periode, atau filter status."
            />
          ))}
      </DataState>
    </div>
  );
}
