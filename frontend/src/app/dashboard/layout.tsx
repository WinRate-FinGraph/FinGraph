"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { getToken, type User } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { canAccessDashboardPath } from "@/lib/access";
import { isDemoBuild } from "@/lib/runtime";
import { SubscriptionProvider } from "@/components/providers/subscription-provider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = getToken();

    if (!token) {
      router.replace("/login");
      return;
    }

    const path = window.location.pathname;
    void apiFetch<User>("/auth/me")
      .then((current) => {
        localStorage.setItem("fingraph_user", JSON.stringify(current));
        if (!isDemoBuild && path.startsWith("/dashboard/simulation")) {
          router.replace("/dashboard");
          return;
        }
        if (!canAccessDashboardPath(current.role, path, current.subscription_plan)) {
          router.replace(
            current.role === "merchant"
              ? `/dashboard/plans?from=${encodeURIComponent(path)}`
              : "/dashboard",
          );
          return;
        }
        setUser(current);
        setReady(true);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-background" aria-label="Menyiapkan ruang kerja">
        <div className="h-16 border-b border-border bg-surface" />
        <div className="mx-auto w-full max-w-[1320px] animate-pulse space-y-6 px-4 py-7 sm:px-6 lg:px-8">
          <div className="h-8 w-56 rounded-lg bg-muted" />
          <div className="h-20 rounded-xl bg-muted" />
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-24 bg-surface" />
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <div className="h-72 rounded-xl border border-border bg-surface" />
            <div className="h-72 rounded-xl border border-border bg-surface" />
          </div>
          <span className="sr-only">Menyiapkan ruang kerja…</span>
        </div>
      </div>
    );
  }

  if (!user) return null;
  return (
    <SubscriptionProvider user={user}>
      <DashboardShell user={user}>{children}</DashboardShell>
    </SubscriptionProvider>
  );
}
