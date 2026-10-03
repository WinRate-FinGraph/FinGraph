import Link from "next/link";
import { ArrowRight, CircleDot } from "lucide-react";

import { StatusBadge } from "@/components/product/ui";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { ActivityItem } from "@/lib/types";

export function ActivityRoleDistribution({
  values,
}: {
  values: Record<string, number>;
}) {
  const roles = [
    { key: "merchant", label: "Merchant", color: "bg-success" },
    { key: "analyst", label: "Analyst", color: "bg-info" },
    { key: "admin", label: "Admin", color: "bg-warning" },
    { key: "system", label: "Sistem", color: "bg-muted-foreground" },
  ];
  const total = Math.max(
    roles.reduce((sum, item) => sum + (values[item.key] ?? 0), 0),
    1,
  );
  return (
    <div className="space-y-4">
      {roles.map((item) => (
        <div key={item.key}>
          <div className="mb-1.5 flex items-center justify-between gap-4 text-sm">
            <span className="font-medium">{item.label}</span>
            <span className="font-technical text-xs text-muted-foreground">
              {values[item.key] ?? 0}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-subtle">
            <div
              className={`h-full rounded-full ${item.color}`}
              style={{ width: `${((values[item.key] ?? 0) / total) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ActivityList({
  items,
  compact = false,
}: {
  items: ActivityItem[];
  compact?: boolean;
}) {
  return (
    <div className="divide-y divide-border">
      {items.map((item) => (
        <article
          key={item.id}
          className="flex items-start gap-3 px-4 py-4 sm:px-5"
        >
          <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-surface-subtle text-primary">
            <CircleDot className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-sm font-medium">{item.actor}</p>
              <StatusBadge kind="profile" value={item.actor_role} />
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {humanDescription(item.description) || humanAction(item.action)}
            </p>
            {item.impact && !compact && (
              <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl bg-surface-subtle px-3 py-2 text-xs">
                <span className="font-medium">
                  {formatCurrency(item.impact.amount, item.impact.currency)}
                </span>
                <span>{item.impact.category}</span>
                <span>Prioritas {item.impact.priority}</span>
                <Link
                  href={`/dashboard/payments/${item.impact.payment_id}`}
                  className="ml-auto inline-flex items-center font-medium text-primary"
                >
                  Lihat dampak
                  <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </div>
            )}
            <p className="mt-1.5 text-xs text-muted-foreground">
              {formatDateTime(item.created_at)}
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}

export function humanAction(value: string) {
  const labels: Record<string, string> = {
    login_user: "Pengguna masuk",
    register_user: "Akun dibuat",
    run_qris_demo_scenario: "Skenario pembayaran dijalankan",
    generate_demo_payment: "Pembayaran contoh dibuat",
    process_pjp_webhook: "Pembayaran dikonfirmasi",
    create_payment_feedback: "Keputusan manusia dicatat",
    update_alert_status: "Status peringatan diperbarui",
    rescore_payment: "Risiko dihitung ulang",
  };
  if (labels[value]) return labels[value];
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function humanDescription(value?: string | null) {
  if (!value) return "";
  const translations: Record<string, string> = {
    "User logged in successfully.": "Pengguna berhasil masuk.",
  };
  if (translations[value]) return translations[value];
  const scenario = value.match(/^Skenario ([a-z0-9_]+) dijalankan/i);
  if (scenario) return `Skenario pembayaran “${scenario[1].replaceAll("_", " ")}” dijalankan dalam Mode Demo.`;
  return value.replace(/Feedback (fraud|legitimate|suspicious)\/(approve|verify|hold|report)/i, "Feedback review manusia");
}
