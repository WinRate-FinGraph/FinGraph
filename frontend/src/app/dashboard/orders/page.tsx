"use client";

import { FormEvent, useMemo, useState } from "react";
import { Copy, Plus, ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import {
  DataState,
  EmptyState,
  FilterBar,
  PageHeader,
  PaginationBar,
  SearchInput,
  StatusBadge,
} from "@/components/product/ui";
import { useSelectedOutlet } from "@/components/providers/outlet-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import { humanizeOrderDescription } from "@/lib/presentation";
import type { Order, PageResponse } from "@/lib/types";

const statusFilters = [
  { value: "all", label: "Semua" },
  { value: "awaiting_payment", label: "Menunggu" },
  { value: "paid", label: "Dibayar" },
  { value: "held", label: "Ditahan" },
  { value: "completed", label: "Selesai" },
];

export default function OrdersPage() {
  const outlets = useApi<{ items: { id: string; name: string }[] }>(
    "/merchants/outlets",
  );
  const { selectedId } = useSelectedOutlet();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [created, setCreated] = useState<Order | null>(null);
  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (status !== "all") params.set("status", status);
    if (search.trim()) params.set("search", search.trim());
    if (selectedId !== "all") params.set("outlet_id", selectedId);
    return `/orders?${params}`;
  }, [offset, search, selectedId, status]);
  const orders = useApi<PageResponse<Order>>(path);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      const result = await apiFetch<Order>("/orders", {
        method: "POST",
        body: JSON.stringify({
          outlet_id: form.get("outlet_id"),
          expected_amount: Number(form.get("expected_amount")),
          currency: "IDR",
          description: form.get("description"),
          expires_at: form.get("expires_at") || null,
        }),
      });
      setCreated(result);
      toast.success("Pesanan berhasil dibuat");
      await orders.reload();
    } catch (reason) {
      toast.error(
        reason instanceof Error ? reason.message : "Pesanan belum dapat dibuat",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="space-y-6">
      <PageHeader
        title="Pesanan"
        description="Pantau status pembayaran setiap pesanan dari satu tempat."
        action={
          <Button
            onClick={() => {
              setCreated(null);
              setOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Buat Pesanan
          </Button>
        }
      />
      <Tabs
        value={status}
        onValueChange={(value) => {
          setStatus(value);
          setOffset(0);
        }}
      >
        <TabsList className="w-fit max-w-full justify-start rounded-xl bg-secondary p-1">
          {statusFilters.map((item) => (
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
          placeholder="Cari nomor pesanan atau deskripsi…"
        />
      </FilterBar>
      <DataState
        loading={orders.loading}
        error={orders.error}
        onRetry={orders.reload}
      >
        {orders.data &&
          (orders.data.items.length ? (
            <>
              <OrderTable items={orders.data.items} />
              <PaginationBar
                total={orders.data.total}
                limit={orders.data.limit}
                offset={orders.data.offset}
                onPageChange={setOffset}
              />
            </>
          ) : (
            <EmptyState
              icon={ShoppingBag}
              title="Pesanan tidak ditemukan"
              description="Buat pesanan baru atau ubah filter pencarian."
              action={
                <Button onClick={() => setOpen(true)}>Buat pesanan</Button>
              }
            />
          ))}
      </DataState>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>{created ? "Pesanan siap" : "Buat pesanan"}</SheetTitle>
            <SheetDescription>
              {created
                ? "Bagikan referensi ini atau tunggu pembayaran masuk."
                : "Catat nominal sebelum pelanggan melakukan pembayaran."}
            </SheetDescription>
          </SheetHeader>
          {created ? (
            <div className="px-4 pb-6">
              <div className="mt-6 rounded-xl border bg-secondary p-5">
                <p className="text-sm text-muted-foreground">Nomor pesanan</p>
                <p className="mt-2 break-all font-technical text-sm font-medium">
                  {created.order_reference}
                </p>
                <p className="mt-5 text-sm text-muted-foreground">Total</p>
                <p className="mt-1 text-2xl font-medium">
                  {formatCurrency(created.expected_amount)}
                </p>
              </div>
              <div className="mt-5 grid gap-2">
                <Button
                  onClick={() => {
                    void navigator.clipboard.writeText(created.order_reference);
                    toast.success("Referensi disalin");
                  }}
                >
                  <Copy className="mr-2 h-4 w-4" />
                  Salin referensi
                </Button>
                <Button variant="outline" onClick={() => setOpen(false)}>
                  Tunggu pembayaran
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={create} className="space-y-5 px-4 pb-6 pt-5">
              <div className="space-y-2">
                <Label htmlFor="outlet_id">Outlet</Label>
                <Select name="outlet_id" required>
                  <SelectTrigger id="outlet_id" className="h-12 w-full">
                    <SelectValue placeholder="Pilih outlet" />
                  </SelectTrigger>
                  <SelectContent>
                    {outlets.data?.items.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="expected_amount">Nominal pesanan</Label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-medium text-muted-foreground">
                    Rp
                  </span>
                  <Input
                    id="expected_amount"
                    name="expected_amount"
                    required
                    type="number"
                    inputMode="numeric"
                    min={1}
                    placeholder="350000"
                    className="h-12 pl-11 text-base font-medium"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Deskripsi</Label>
                <Input
                  id="description"
                  name="description"
                  required
                  maxLength={255}
                  placeholder="Contoh: 2 kain batik tulis"
                  className="h-12"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="expires_at">
                  Berlaku sampai{" "}
                  <span className="font-normal text-muted-foreground">
                    (opsional)
                  </span>
                </Label>
                <Input
                  id="expires_at"
                  name="expires_at"
                  type="datetime-local"
                  className="h-12"
                />
              </div>
              <Button disabled={saving} className="h-12 w-full">
                {saving ? "Menyimpan…" : "Simpan pesanan"}
              </Button>
            </form>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function OrderTable({ items }: { items: Order[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-surface-subtle text-xs text-muted-foreground">
            <tr>
              <th className="px-5 py-3.5">Pesanan</th>
              <th className="px-4 py-3.5">Dibuat</th>
              <th className="px-4 py-3.5">Outlet</th>
              <th className="px-4 py-3.5 text-right">Total</th>
              <th className="px-4 py-3.5">Pembayaran</th>
              <th className="px-5 py-3.5">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((order) => (
              <tr
                key={order.id}
                className="h-[68px] transition-colors hover:bg-surface-subtle"
              >
                <td className="max-w-[260px] px-5 py-3.5">
                  <p
                    className="truncate font-medium"
                    title={humanizeOrderDescription(order.description)}
                  >
                    {humanizeOrderDescription(order.description)}
                  </p>
                  <p
                    className="mt-1 max-w-[220px] truncate font-technical text-xs text-muted-foreground"
                    title={order.order_reference}
                  >
                    {order.order_reference}
                  </p>
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-muted-foreground">
                  {formatDateTime(order.created_at)}
                </td>
                <td
                  className="max-w-[160px] truncate px-4 py-3.5 text-muted-foreground"
                  title={order.outlet_name}
                >
                  {order.outlet_name}
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-right font-medium">
                  {formatCurrency(order.expected_amount, order.currency)}
                </td>
                <td className="px-4 py-3.5">
                  {order.latest_payment ? (
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge kind="payment" value={order.latest_payment.payment_status} />
                      <StatusBadge kind="risk" value={order.latest_payment.risk_level} />
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">Belum ada pembayaran</span>
                  )}
                </td>
                <td className="px-5 py-3.5">
                  <StatusBadge kind="order" value={order.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-border md:hidden">
        {items.map((order) => (
          <article key={order.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium">
                  {formatCurrency(order.expected_amount, order.currency)}
                </p>
                <p
                  className="mt-1 max-w-[190px] truncate font-technical text-xs text-muted-foreground"
                  title={order.order_reference}
                >
                  {order.order_reference}
                </p>
              </div>
              <StatusBadge kind="order" value={order.status} />
            </div>
            <p className="mt-3 text-sm">
              {humanizeOrderDescription(order.description)}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {order.outlet_name} · {formatDateTime(order.created_at)}
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {order.latest_payment ? (
                <>
                  <StatusBadge kind="payment" value={order.latest_payment.payment_status} />
                  <StatusBadge kind="risk" value={order.latest_payment.risk_level} />
                </>
              ) : (
                <span className="text-xs text-muted-foreground">Belum ada pembayaran</span>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
