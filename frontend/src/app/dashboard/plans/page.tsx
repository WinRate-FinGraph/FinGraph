"use client";

import { useState } from "react";
import { Info, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { PricingCards, PlanBadge } from "@/components/product/pricing";
import { DataState, PageHeader } from "@/components/product/ui";
import { useSubscription } from "@/components/providers/subscription-provider";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/auth";
import { normalizePlan, planByCode, type PlanCode } from "@/lib/plans";

type SubscriptionResponse = {
  current: {
    code: PlanCode;
    name: string;
    monthly_price: number;
    transaction_limit: number;
    outlet_limit: number | null;
    seat_limit: number;
  };
  status: string;
  changed_at: string | null;
  checkout_available: boolean;
  demo_change_available: boolean;
  notice: string;
};

export default function PlansPage() {
  const query = useApi<SubscriptionResponse>("/merchants/subscription");
  const { plan, setPlan } = useSubscription();
  const [busyPlan, setBusyPlan] = useState<PlanCode | null>(null);

  async function changePlan(nextPlan: PlanCode) {
    if (!query.data?.demo_change_available) {
      toast.info("Hubungi tim FinGraph untuk mengubah paket.");
      return;
    }
    setBusyPlan(nextPlan);
    try {
      const response = await apiFetch<SubscriptionResponse>(
        "/merchants/subscription",
        {
          method: "PATCH",
          body: JSON.stringify({ plan: nextPlan }),
        },
      );
      const current = normalizePlan(response.current.code);
      setPlan(current);
      const user = await apiFetch<User>("/auth/me");
      localStorage.setItem("fingraph_user", JSON.stringify(user));
      toast.success(`Paket demo ${planByCode(current).name} sudah aktif`);
      await query.reload();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Paket belum dapat diubah",
      );
    } finally {
      setBusyPlan(null);
    }
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title="Konsep Paket FinGraph"
        description="Peragakan pembatasan fitur MVP. Harga dan paket ini belum merupakan penawaran komersial final."
        action={<PlanBadge plan={plan} />}
      />

      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {query.data && (
          <>
            <section className="grid gap-4 rounded-xl border border-border bg-surface p-5 sm:grid-cols-[auto_1fr] sm:items-center">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent text-accent-foreground">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-medium">Paket aktif</h2>
                  <PlanBadge plan={normalizePlan(query.data.current.code)} />
                </div>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {query.data.notice}
                </p>
              </div>
            </section>

            <PricingCards
              currentPlan={normalizePlan(query.data.current.code)}
              busyPlan={busyPlan}
              onSelect={changePlan}
            />

            <div className="flex gap-3 rounded-xl bg-info-soft p-4 text-sm leading-6 text-info">
              <Info className="mt-0.5 h-5 w-5 shrink-0" />
              <p>
                Katalog ini belum memproses pembayaran. Pada Mode Demo,
                pergantian paket hanya digunakan untuk memperagakan akses fitur.
                Tidak ada checkout nyata. Aktivasi komersial dan model harga
                final berada di luar cakupan MVP ini.
              </p>
            </div>
          </>
        )}
      </DataState>
    </div>
  );
}
