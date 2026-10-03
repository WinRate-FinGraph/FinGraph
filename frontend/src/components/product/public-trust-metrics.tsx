"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Building2, CircleCheck, Radio, Users } from "lucide-react";

import { Reveal } from "@/components/marketing/reveal";
import { apiFetch } from "@/lib/api";
import type { PublicTrustSummary } from "@/lib/types";

const refreshIntervalMs = 30_000;

function formatCount(value: number) {
  return new Intl.NumberFormat("id-ID").format(value);
}

export function PublicTrustMetrics() {
  const [summary, setSummary] = useState<PublicTrustSummary | null>(null);
  const [error, setError] = useState(false);

  const loadSummary = useCallback(async () => {
    try {
      const nextSummary = await apiFetch<PublicTrustSummary>("/public/trust-summary", {
        cache: "no-store",
      });
      setSummary(nextSummary);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void loadSummary(), 0);
    const timer = window.setInterval(() => void loadSummary(), refreshIntervalMs);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [loadSummary]);

  const metrics = summary
    ? [
        {
          icon: Users,
          value: formatCount(summary.registered_users),
          label: "Akun demo",
          detail: `${formatCount(summary.active_users)} aktif dalam ${summary.activity_window_minutes} menit terakhir`,
        },
        {
          icon: Building2,
          value: formatCount(summary.active_merchants),
            label: "Usaha contoh aktif",
          detail: `${formatCount(summary.active_outlets)} outlet simulasi`,
        },
        {
          icon: Activity,
          value: formatCount(summary.payments_checked),
            label: "Pembayaran diperiksa",
          detail: "Dihitung dari database lokal",
        },
        {
          icon: CircleCheck,
          value: `${summary.verification_rate.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`,
            label: "Pembayaran berisiko rendah",
          detail: `${formatCount(summary.verified_payments)} pembayaran memenuhi kedua kondisi`,
        },
      ]
    : [];

  return (
    <section
      id="dampak"
      aria-labelledby="trust-metrics-title"
      className="border-b border-zinc-800 bg-black py-16 text-white sm:py-20"
    >
      <Reveal className="mx-auto max-w-[1240px] px-4 sm:px-6">
        <div className="flex flex-col gap-6 border-b border-zinc-800 pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs tracking-[.08em] text-zinc-500">AKTIVITAS MODE DEMO</p>
            <h2 id="trust-metrics-title" className="font-display mt-5 max-w-3xl text-[36px] font-light leading-[1.08] tracking-[-.03em] sm:text-[48px]">
              Contoh aktivitas FinGraph.
            </h2>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-zinc-700 px-3 py-2 text-xs text-zinc-300">
            <Radio className="h-3.5 w-3.5" />
            Bukan data adopsi publik
          </span>
        </div>

        {summary ? (
          <>
            <div className="grid divide-y divide-zinc-800 sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-4">
              {metrics.map(({ icon: Icon, value, label, detail }) => (
                <article key={label} className="py-7 sm:px-6 sm:first:pl-0 lg:py-9">
                  <Icon className="h-5 w-5 text-zinc-500" aria-hidden="true" />
                  <p className="font-display mt-7 text-[38px] font-light tracking-[-.03em] sm:text-[44px]">
                    {value}
                  </p>
                  <h3 className="mt-2 text-sm font-medium">{label}</h3>
                  <p className="mt-1 text-xs leading-5 text-zinc-500">{detail}</p>
                </article>
              ))}
            </div>
            <p className="border-t border-zinc-800 pt-4 text-xs text-zinc-500">
              Mode Demo · {summary.data_scope} · Diperbarui{" "}
              {new Intl.DateTimeFormat("id-ID", {
                timeZone: "Asia/Jakarta",
                hour: "2-digit",
                minute: "2-digit",
                day: "numeric",
                month: "short",
              }).format(new Date(summary.updated_at))}{" "}
              WIB
            </p>
          </>
        ) : error ? (
          <div role="status" className="py-10 text-sm text-zinc-400">
            Ringkasan aktivitas sedang tidak tersedia. Fitur utama tetap dapat digunakan.
          </div>
        ) : (
          <div aria-label="Memuat data aktivitas FinGraph" className="grid gap-5 py-8 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((item) => (
              <div key={item} className="h-32 animate-pulse rounded-xl bg-zinc-900" />
            ))}
          </div>
        )}
      </Reveal>
    </section>
  );
}
