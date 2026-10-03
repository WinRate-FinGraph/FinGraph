"use client";
import {
  DataState,
  EmptyState,
  PageHeader,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import { useApi } from "@/hooks/use-api";
import { formatCurrency } from "@/lib/format";
type Summary = {
  total_payments: number;
  domestic_same_region: number;
  cross_region_payments: number;
  cross_border_payments: number;
  average_fraud_score: number;
  high_risk_count: number;
  total_value: number;
  note: string;
};
type Route = {
  route: string;
  transaction_count: number;
  total_amount: number;
  average_fraud_score: number;
  high_risk_count: number;
  high_risk_rate: number;
  route_status: "normal" | "monitor" | "high";
  status_reason: string;
};
export default function CrossBorderPage() {
  const summary = useApi<Summary>("/cross-border/summary");
  const routes = useApi<{ items: Route[] }>("/cross-border/routes");
  return (
    <div className="space-y-6">
      <PageHeader
        title="Lintas Wilayah"
        description="Analisis perpindahan pembayaran antarkota, platform, dan negara sebagai konteks risiko tambahan."
      />
      <DataState
        loading={summary.loading}
        error={summary.error}
        onRetry={summary.reload}
      >
        {summary.data && (
          <SummaryStrip
            items={[
              {
                label: "Domestik lokal",
                value: summary.data.domestic_same_region,
              },
              {
                label: "Lintas wilayah",
                value: summary.data.cross_region_payments,
                tone: "info",
              },
              {
                label: "Lintas negara",
                value: summary.data.cross_border_payments,
                tone: "warning",
              },
              {
                label: "Risiko tinggi",
                value: summary.data.high_risk_count,
                tone: "danger",
              },
            ]}
          />
        )}
      </DataState>
      <section className="overflow-hidden rounded-xl border bg-card">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h2 className="font-medium">Rute pembayaran</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Lintas wilayah tidak otomatis dianggap berisiko.
            </p>
          </div>
          {summary.data && (
            <span className="text-sm font-medium">
              {formatCurrency(summary.data.total_value)}
            </span>
          )}
        </div>
        <DataState
          loading={routes.loading}
          error={routes.error}
          onRetry={routes.reload}
        >
          {routes.data &&
            (routes.data.items.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b bg-secondary/60 text-xs text-muted-foreground">
                    <tr>
                      <th className="px-5 py-3.5">Rute</th>
                      <th className="px-4 py-3.5 text-right">Transaksi</th>
                      <th className="px-4 py-3.5 text-right">Nilai</th>
                      <th className="px-4 py-3.5 text-right">Skor rata-rata</th>
                      <th className="px-5 py-3.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {routes.data.items.map((route) => (
                      <tr key={route.route}>
                        <td className="px-5 py-4 font-medium">{route.route}</td>
                        <td className="px-4 py-4 text-right">
                          {route.transaction_count}
                        </td>
                        <td className="px-4 py-4 text-right font-medium">
                          {formatCurrency(route.total_amount)}
                        </td>
                        <td className="px-4 py-4 text-right font-technical text-xs">
                          {Math.round(route.average_fraud_score * 100)}%
                        </td>
                        <td className="px-5 py-4" title={route.status_reason}>
                          <StatusBadge
                            value={
                              route.route_status === "normal"
                                ? "low"
                                : route.route_status === "monitor"
                                  ? "medium"
                                  : "high"
                            }
                          />
                          <p className="mt-1 max-w-52 text-xs leading-5 text-muted-foreground">
                            {route.status_reason}
                          </p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="Belum ada rute pembayaran" />
            ))}
        </DataState>
      </section>
    </div>
  );
}
