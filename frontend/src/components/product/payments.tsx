"use client";

import Link from "next/link";
import { ArrowRight, History, ReceiptText } from "lucide-react";
import { AIAnalysisInline, StatusBadge } from "@/components/product/ui";
import { formatCurrency, formatTime } from "@/lib/format";
import { paymentDecision } from "@/lib/presentation";
import type { Payment } from "@/lib/types";
import { useSubscription } from "@/components/providers/subscription-provider";
import { planAtLeast } from "@/lib/plans";

export function PaymentTable({
  items,
  analyst = false,
}: {
  items: Payment[];
  analyst?: boolean;
}) {
  const { plan } = useSubscription();
  const showGrowthFeatures = analyst || planAtLeast(plan, "growth");
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="hidden overflow-x-auto md:block">
        <table className={showGrowthFeatures ? "w-full min-w-[1180px] table-fixed text-left text-sm" : "w-full min-w-[1000px] table-fixed text-left text-sm"}>
          <thead className="border-b border-border bg-surface-subtle text-xs font-medium text-muted-foreground">
            <tr>
              <th className="w-[68px] px-4 py-3.5">Waktu</th>
              <th className="w-[126px] px-3 py-3.5">Referensi</th>
              <th className="w-[116px] px-3 py-3.5">Pesanan</th>
              {showGrowthFeatures && <th className="w-[74px] px-3 py-3.5">Kategori</th>}
              {showGrowthFeatures && <th className="w-[88px] px-3 py-3.5">Prioritas</th>}
              <th className="w-[104px] px-3 py-3.5 text-right">Nominal</th>
              <th className="w-[116px] px-3 py-3.5">Outlet</th>
              <th className="w-[126px] px-3 py-3.5">Status pembayaran</th>
              <th className="w-[130px] px-3 py-3.5">Risiko</th>
              <th className="w-[150px] px-3 py-3.5">Rekomendasi</th>
              <th className="w-[126px] px-4 py-3.5 text-right">Tindakan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item) => (
              <PaymentTableRow key={item.id} item={item} analyst={analyst} showGrowthFeatures={showGrowthFeatures} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-border md:hidden">
        {items.map((item) => (
          <PaymentListItem key={item.id} item={item} showGrowthFeatures={showGrowthFeatures} />
        ))}
      </div>
    </div>
  );
}

function PaymentTableRow({
  item,
  analyst,
  showGrowthFeatures,
}: {
  item: Payment;
  analyst: boolean;
  showGrowthFeatures: boolean;
}) {
  const decision = paymentDecision({
    providerStatus: item.payment_status,
    callbackReceived: item.callback_received,
    riskLevel: item.risk_level,
    recommendationCode: item.recommendation_code,
  });
  return (
    <tr className="h-[72px] transition-colors hover:bg-surface-subtle">
      <td className="whitespace-nowrap px-4 py-3.5 text-muted-foreground">
        {formatTime(item.transaction_time)}
      </td>
      <td className="px-3 py-3.5">
        <span
          className="block truncate font-technical text-xs font-medium"
          title={item.provider_reference}
        >
          {item.provider_reference}
        </span>
        {analyst && item.payer_pseudonym && (
          <span
            className="mt-1 block max-w-[160px] truncate text-xs text-muted-foreground"
            title={item.payer_pseudonym}
          >
            {item.payer_pseudonym}
          </span>
        )}
      </td>
      <td
        className="truncate px-3 py-3.5 text-muted-foreground"
        title={item.order_reference ?? undefined}
      >
        {item.order_reference ?? "—"}
      </td>
      {showGrowthFeatures && (
        <td className="truncate px-3 py-3.5" title={item.category}>
          {item.category}
        </td>
      )}
      {showGrowthFeatures && (
        <td className="px-3 py-3.5">
          <PriorityBadge value={item.priority} />
        </td>
      )}
      <td className="whitespace-nowrap px-3 py-3.5 text-right font-medium">
        {formatCurrency(item.amount, item.currency)}
      </td>
      <td
        className="truncate px-3 py-3.5 text-muted-foreground"
        title={item.outlet_name}
      >
        {item.outlet_name}
      </td>
      <td className="px-3 py-3.5">
        <StatusBadge kind="payment" value={item.payment_status} />
      </td>
      <td className="px-3 py-3.5">
        <StatusBadge kind="risk" value={item.risk_level} />
        <div className="mt-1">
        <AIAnalysisInline
          score={item.fraud_score}
          confidence={item.confidence_score}
        />
        </div>
      </td>
      <td className="px-3 py-3.5">
        <span className="text-xs font-medium">{decision.label}</span>
      </td>
      <td className="px-4 py-3.5 text-right">
        <div className="flex justify-end gap-1">
          {showGrowthFeatures && (
            <Link
              href={`/dashboard/audit-logs?entity_id=${item.id}`}
              aria-label={`Lihat riwayat aksi ${item.provider_reference}`}
              title="Lihat riwayat aksi"
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-primary"
            >
              <History className="h-4 w-4" />
            </Link>
          )}
          <Link
            href={`/dashboard/payments/${item.id}`}
            aria-label={`Tinjau pembayaran ${item.provider_reference}`}
            className="inline-flex min-h-10 items-center rounded-lg px-2 font-medium text-primary hover:bg-accent hover:no-underline"
          >
            Tinjau <ArrowRight className="ml-1.5 h-4 w-4" />
          </Link>
        </div>
      </td>
    </tr>
  );
}

export function PaymentListItem({
  item,
  compact = false,
  showGrowthFeatures,
}: {
  item: Payment;
  compact?: boolean;
  showGrowthFeatures?: boolean;
}) {
  const decision = paymentDecision({
    providerStatus: item.payment_status,
    callbackReceived: item.callback_received,
    riskLevel: item.risk_level,
    recommendationCode: item.recommendation_code,
  });
  return (
    <Link
      href={`/dashboard/payments/${item.id}`}
      className="group flex min-h-[102px] items-center gap-3.5 px-4 py-3.5 transition-colors hover:bg-surface-subtle sm:px-5"
    >
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-subtle text-primary">
        <ReceiptText className="h-[18px] w-[18px]" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <p className="font-medium tracking-[-.015em]">
            {formatCurrency(item.amount, item.currency)}
          </p>
          <span className="flex flex-wrap justify-end gap-1.5">
            <StatusBadge kind="payment" value={item.payment_status} />
            <StatusBadge kind="risk" value={item.risk_level} />
          </span>
        </div>
        <div className="mt-1.5 flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
          <span className="shrink-0">{formatTime(item.transaction_time)}</span>
          <span aria-hidden>·</span>
          <span
            className="truncate font-technical"
            title={item.provider_reference}
          >
            {item.provider_reference}
          </span>
          {!compact && (
            <>
              <span aria-hidden>·</span>
              <span className="hidden truncate sm:inline">
                {item.outlet_name}
              </span>
            </>
          )}
        </div>
        <p className="mt-1 truncate text-xs font-[580] text-muted-foreground">
          {showGrowthFeatures
            ? `${item.category} · prioritas ${item.priority} · ${decision.label}`
            : decision.label}
        </p>
        <div className="mt-1">
          <AIAnalysisInline
            score={item.fraud_score}
            confidence={item.confidence_score}
          />
        </div>
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

function PriorityBadge({ value }: { value: Payment["priority"] }) {
  const classes =
    value === "tinggi"
      ? "border-danger/25 bg-danger-soft text-danger"
      : value === "sedang"
        ? "border-warning/25 bg-warning-soft text-warning"
        : "border-success/25 bg-success-soft text-success";
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-xs font-medium ${classes}`}
    >
      {value[0].toUpperCase() + value.slice(1)}
    </span>
  );
}
