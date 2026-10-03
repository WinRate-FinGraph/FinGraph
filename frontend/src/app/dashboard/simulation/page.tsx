"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { FlaskConical, Play } from "lucide-react";
import { toast } from "sonner";
import { DataState, DemoModeBanner, PageHeader, StatusBadge } from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { humanizeScenarioName, paymentDecision } from "@/lib/presentation";

type Scenario = { name: string; description: string };
type PaymentResult = {
  id: string;
  provider_reference: string;
  payment_status: string;
  callback_received?: boolean;
  fraud_score: number;
  risk_level: string;
  recommendation: string;
  recommendation_code?: string;
};
type RunResult = { scenario: string; payment: PaymentResult; alert_created: boolean };
type Merchant = { id: string; name: string };
type Outlet = { id: string; name: string };
type GeneratedPayment = { payment: PaymentResult; webhook: { payload: Record<string, unknown>; signature: string } };

export default function DemoLabPage() {
  const scenarios = useApi<{ items: Scenario[] }>("/demo/qris/scenarios");
  const merchants = useApi<{ items: Merchant[] }>("/merchants?limit=100");
  const [merchantId, setMerchantId] = useState("");
  const selectedMerchantId = merchantId || merchants.data?.items[0]?.id || "";
  const outlets = useApi<{ items: Outlet[] }>(selectedMerchantId ? `/merchants/outlets?merchant_id=${selectedMerchantId}` : null);
  const [running, setRunning] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [customSummary, setCustomSummary] = useState("");

  async function run(name: string) {
    setRunning(name);
    try {
      const value = await apiFetch<RunResult>(`/demo/qris/scenarios/${name}${selectedMerchantId ? `?merchant_id=${selectedMerchantId}` : ""}`, { method: "POST" });
      setResult(value);
      setCustomSummary("");
      toast.success("Skenario selesai dijalankan");
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "Skenario belum dapat dijalankan");
    } finally {
      setRunning("");
    }
  }

  async function runCustom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const outletId = String(form.get("outlet_id") || "");
    if (!selectedMerchantId || !outletId) return toast.error("Pilih merchant dan outlet");
    setRunning("custom");
    try {
      const expected = Number(form.get("expected_amount"));
      const paid = Number(form.get("paid_amount"));
      const paymentStatus = String(form.get("payment_status"));
      const sendCallback = form.get("send_callback") === "on";
      const order = await apiFetch<{ id: string }>(`/demo/qris/create-order?merchant_id=${selectedMerchantId}`, {
        method: "POST",
        body: JSON.stringify({ outlet_id: outletId, expected_amount: expected, currency: "IDR", description: "Simulasi kustom Demo Lab", customer_reference: "demo-lab-customer" }),
      });
      const generated = await apiFetch<GeneratedPayment>("/demo/qris/generate-payment", {
        method: "POST",
        body: JSON.stringify({
          order_id: order.id,
          amount: paid,
          payer_identifier: String(form.get("payer_identifier")),
          source_city: String(form.get("source_city")),
          source_region: String(form.get("source_region")),
          source_country: String(form.get("source_country")),
          payment_status: paymentStatus,
        }),
      });
      let payment = generated.payment;
      let alertCreated = false;
      if (sendCallback) {
        const callback = await apiFetch<{ payment: PaymentResult; alert_created: boolean }>("/demo/qris/webhook", {
          method: "POST",
          headers: { "X-PJP-Signature": generated.webhook.signature },
          body: JSON.stringify(generated.webhook.payload),
        });
        payment = callback.payment;
        alertCreated = callback.alert_created;
      }
      setResult({ scenario: "custom", payment, alert_created: alertCreated });
      setCustomSummary(`Pesanan Rp${expected.toLocaleString("id-ID")} · dibayar Rp${paid.toLocaleString("id-ID")} · ${sendCallback ? "sudah dikonfirmasi" : "belum dikonfirmasi"}`);
      toast.success("Pembayaran contoh dibuat");
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "Pembayaran belum dapat dibuat");
    } finally {
      setRunning("");
    }
  }

  const decision = result ? paymentDecision({ providerStatus: result.payment.payment_status, callbackReceived: result.payment.callback_received, riskLevel: result.payment.risk_level, recommendationCode: result.payment.recommendation_code }) : null;

  return (
    <div className="space-y-6">
      <PageHeader title="Demo FinGraph" description="Buat contoh pembayaran, lihat hasil pemeriksaan, dan coba beberapa kasus. Tidak ada transaksi QRIS nyata." />
      <DemoModeBanner />
      {result && decision && (
        <section className="flex flex-col gap-4 rounded-xl border bg-card p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge kind="payment" value={result.payment.payment_status} />
              <StatusBadge kind="risk" value={decision.risk} />
              <span className="font-technical text-xs text-muted-foreground">{result.payment.provider_reference}</span>
            </div>
            <p className="mt-3 font-medium">{decision.label}</p>
            <p className="mt-1 text-sm text-muted-foreground">{customSummary || humanizeScenarioName(result.scenario)} · risiko {Math.round(result.payment.fraud_score * 100)}/100 · {result.alert_created ? "peringatan dibuat" : "tanpa peringatan"}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild><Link href={`/dashboard/payments/${result.payment.id}`}>Buka pembayaran</Link></Button>
            <Button asChild variant="outline"><Link href={`/dashboard/graph?search=${encodeURIComponent(result.payment.provider_reference)}`}>Lihat hubungan</Link></Button>
            <Button asChild variant="outline"><Link href={`/dashboard/audit-logs?entity_id=${result.payment.id}`}>Lihat riwayat</Link></Button>
          </div>
        </section>
      )}

      <section className="rounded-xl border bg-card p-5 sm:p-6">
        <div className="flex items-start gap-3"><FlaskConical className="mt-0.5 h-5 w-5 text-primary" /><div><h2 className="font-medium">Buat pembayaran contoh</h2><p className="mt-1 text-sm text-muted-foreground">Coba alur pembayaran dengan nominal, status, dan lokasi yang bisa diatur sendiri.</p></div></div>
        <form onSubmit={runCustom} className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Merchant"><Select value={selectedMerchantId} onValueChange={setMerchantId}><SelectTrigger><SelectValue placeholder="Pilih merchant" /></SelectTrigger><SelectContent>{merchants.data?.items.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Outlet"><Select name="outlet_id" defaultValue={outlets.data?.items[0]?.id} key={`${selectedMerchantId}-${outlets.data?.items[0]?.id ?? "none"}`}><SelectTrigger><SelectValue placeholder="Pilih outlet" /></SelectTrigger><SelectContent>{outlets.data?.items.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Status pembayaran"><Select name="payment_status" defaultValue="success"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["success", "failed", "expired", "reversed", "refunded"].map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Nominal pesanan"><Input name="expected_amount" type="number" min="1" defaultValue="350000" required /></Field>
          <Field label="Nominal dibayar"><Input name="paid_amount" type="number" min="1" defaultValue="350000" required /></Field>
          <Field label="Nama pembayar"><Input name="payer_identifier" defaultValue="demo-lab-payer" required /></Field>
          <Field label="Kota"><Input name="source_city" defaultValue="Surakarta" required /></Field>
          <Field label="Provinsi"><Input name="source_region" defaultValue="Jawa Tengah" required /></Field>
          <Field label="Negara"><Input name="source_country" defaultValue="ID" maxLength={3} required /></Field>
          <label className="flex min-h-11 items-center gap-3 rounded-lg border px-3 text-sm sm:col-span-2"><input name="send_callback" type="checkbox" defaultChecked className="h-4 w-4" /> Kirim konfirmasi pembayaran</label>
          <Button disabled={Boolean(running)} className="min-h-11"><Play className="mr-2 h-4 w-4" />{running === "custom" ? "Menjalankan…" : "Buat pembayaran"}</Button>
        </form>
        <p className="mt-4 text-xs text-muted-foreground">Butuh mengecek referensi yang sudah ada? <Link href="/dashboard/payments/check" className="font-medium text-primary">Buka Cek Pembayaran</Link>.</p>
      </section>

      <section><h2 className="font-medium">Contoh kasus</h2><p className="mt-1 text-sm text-muted-foreground">Contoh kasus yang bisa dijalankan berulang kali.</p></section>
      <DataState loading={scenarios.loading} error={scenarios.error} empty={scenarios.data?.items.length === 0} onRetry={scenarios.reload}>
        {scenarios.data && <section className="overflow-hidden rounded-xl border bg-card"><div className="divide-y">{scenarios.data.items.map((item) => (
          <div key={item.name} className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0"><p className="font-medium">{humanizeScenarioName(item.name)}</p><p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted-foreground">{item.description}</p><details className="mt-2 text-xs text-muted-foreground"><summary className="cursor-pointer">Kode teknis</summary><code>{item.name}</code></details></div>
            <Button className="shrink-0" variant="outline" disabled={Boolean(running)} onClick={() => run(item.name)}><Play className="mr-2 h-4 w-4" />{running === item.name ? "Menjalankan…" : "Jalankan"}</Button>
          </div>
        ))}</div></section>}
      </DataState>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-2"><Label>{label}</Label>{children}</div>;
}
