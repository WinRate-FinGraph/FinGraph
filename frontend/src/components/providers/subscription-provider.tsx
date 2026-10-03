"use client";

import { createContext, useContext, useMemo, useState } from "react";

import type { User } from "@/lib/auth";
import { normalizePlan, type PlanCode } from "@/lib/plans";

type SubscriptionContextValue = {
  plan: PlanCode;
  setPlan: (plan: PlanCode) => void;
};

const SubscriptionContext = createContext<SubscriptionContextValue>({
  plan: "basic",
  setPlan: () => undefined,
});

export function SubscriptionProvider({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  const [plan, setPlan] = useState<PlanCode>(
    normalizePlan(user.subscription_plan),
  );
  const value = useMemo(() => ({ plan, setPlan }), [plan]);
  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  return useContext(SubscriptionContext);
}
