"use client";

import Link from "next/link";
import { ArrowRight, Check, Crown, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  formatPlanPrice,
  planCatalog,
  type PlanCode,
} from "@/lib/plans";
import { cn } from "@/lib/utils";

export function PlanBadge({
  plan,
  compact = false,
}: {
  plan: PlanCode;
  compact?: boolean;
}) {
  const definition = planCatalog.find((item) => item.code === plan)!;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        plan === "premium"
          ? "border-warning/30 bg-warning-soft text-warning"
          : plan === "growth"
            ? "border-primary/20 bg-accent text-accent-foreground"
            : "border-border bg-surface-subtle text-muted-foreground",
      )}
    >
      {plan === "premium" && <Crown className="h-3 w-3" />}
      {!compact && "Paket "}
      {definition.name}
    </span>
  );
}

export function PricingCards({
  currentPlan,
  busyPlan,
  onSelect,
  publicCtaHref = "/login",
}: {
  currentPlan?: PlanCode;
  busyPlan?: PlanCode | null;
  onSelect?: (plan: PlanCode) => void;
  publicCtaHref?: string;
}) {
  return (
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3 lg:items-stretch">
      {planCatalog.map((plan) => {
        const active = currentPlan === plan.code;
        return (
          <article
            key={plan.code}
            className={cn(
              "relative flex min-w-0 flex-col rounded-xl border border-border bg-surface p-6 shadow-[0_8px_8px_rgba(0,0,0,.08),0_4px_4px_rgba(0,0,0,.08),0_2px_2px_rgba(0,0,0,.08),0_0_0_1px_rgba(0,0,0,.06)] sm:p-8",
              plan.featured &&
                "border-transparent bg-accent shadow-[0_8px_8px_rgba(0,0,0,.08),0_4px_4px_rgba(0,0,0,.08),0_2px_2px_rgba(0,0,0,.08),0_0_0_1px_rgba(0,0,0,.06)]",
            )}
          >
            {plan.featured && (
              <span className="mb-5 inline-flex w-fit items-center gap-1.5 rounded-full bg-black px-3 py-1.5 text-xs font-medium text-white">
                <Sparkles className="h-3.5 w-3.5" />
                Pilihan paling seimbang
              </span>
            )}
            <div>
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-display text-[28px] font-medium leading-tight tracking-[.01em]">
                  {plan.name}
                </h3>
                {active && <PlanBadge plan={plan.code} compact />}
              </div>
              <p className="mt-3 min-h-10 text-sm leading-5 text-muted-foreground">
                {plan.audience}
              </p>
              <div className="mt-5 flex items-end gap-1.5">
                <span className="font-display text-[46px] font-light leading-none tracking-[-.035em]">
                  {formatPlanPrice(plan.price)}
                </span>
                <span className="pb-1 text-sm text-muted-foreground">
                  /bulan
                </span>
              </div>
              <p className="mt-4 min-h-12 text-sm leading-6 text-muted-foreground">
                {plan.summary}
              </p>
            </div>

            <div className="my-5 h-px bg-border" />
            <ul className="flex-1 space-y-3">
              {plan.features.map((feature) => (
                <li key={feature} className="flex gap-2.5 text-sm leading-5">
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground">
                    <Check className="h-3 w-3" strokeWidth={2.8} />
                  </span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <div className={cn("mt-6 rounded-xl p-4 text-xs leading-5 text-muted-foreground", plan.featured ? "bg-white/55" : "bg-surface-subtle")}>
              <p>
                <strong className="text-foreground">
                  {plan.transactionLimit.toLocaleString("id-ID")}
                </strong>{" "}
                transaksi/bulan
                {" · "}
                {plan.outletLimit ? `${plan.outletLimit} outlet` : "Multi outlet"}
                {" · "}
                {plan.seatLimit === 1
                  ? "1 akun"
                  : `${plan.seatLimit}${plan.code === "premium" ? "+" : ""} akun`}
              </p>
              <p className="mt-1">{plan.support}</p>
            </div>

            {onSelect ? (
              <Button
                type="button"
                variant={plan.featured ? "default" : "outline"}
                className="mt-5 h-11 w-full"
                disabled={active || busyPlan !== null}
                onClick={() => onSelect(plan.code)}
              >
                {busyPlan === plan.code
                  ? "Menerapkan…"
                  : active
                    ? "Paket saat ini"
                    : `Pilih ${plan.name}`}
              </Button>
            ) : (
              <Button
                asChild
                variant={plan.featured ? "default" : "outline"}
                className="mt-5 h-11 w-full"
              >
                <Link href={publicCtaHref}>
                  Coba paket {plan.name}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            )}
          </article>
        );
      })}
    </div>
  );
}
