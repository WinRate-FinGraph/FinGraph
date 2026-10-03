"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  QrCode,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";
import {
  AmountComparison,
  AIAnalysisCard,
  DecisionBanner,
  DetailList,
  InlineLoader,
  GnnScoreSummary,
  PageHeader,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { paymentDecision, splitReasons } from "@/lib/presentation";

type Result = {
  found: boolean;
  provider_status: string;
  amount_match: boolean;
  order_match?: boolean;
  payment?: {
    id: string;
    risk_level: string;
    recommendation: string;
    recommendation_code?: string;
    fraud_score: number;
    amount?: number;
    expected_amount?: number | null;
    currency?: string;
    callback_received?: boolean;
    callback_received_at?: string;
  };
  risk_result: {
    risk_level: string;
    final_score: number;
    confidence_score?: number;
    analysis_mode?: "ensemble_ai" | "ensemble_gnn" | "rule_graph_fallback";
    recommendation: string;
    recommendation_code?: string;
    reasons: string[];
    gnn_score?: number | null;
    gnn_final_weight?: number;
    legacy_ensemble_score?: number;
    gnn_metadata?: { model_version?: string | null; fallback_reason?: string | null };
  };
  demo_notice: string;
};

export default function CheckPaymentPage() {
  const outlets = useApi<{ items: { id: string; name: string }[] }>(
    "/merchants/outlets",
  );
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("");
  const [order, setOrder] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResult(
        await apiFetch<Result>("/payments/check", {
          method: "POST",
          body: JSON.stringify({
            provider_reference: reference.trim(),
            amount: Number(amount),
            order_reference: order.trim() || null,
          }),
        }),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Pemeriksaan belum dapat dilakukan",
      );
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setError("");
  }

  function fillSample(entered: string) {
    setReference("PJP-DEMO-0001");
    setAmount(entered);
    setOrder("ORD-DEMO-001");
    setResult(null);
    setError("");
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link
        href="/dashboard/payments"
        className="inline-flex min-h-10 items-center text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Kembali ke pembayaran
      </Link>
      <PageHeader
        title="Cek Pembayaran"
        description="Pastikan dana sudah masuk sebelum pesanan diserahkan."
      />
      {!result ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <form
            onSubmit={submit}
            className="rounded-xl border bg-card p-5 surface-raised sm:p-7"
          >
            <div className="mb-6 flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-primary">
                <QrCode className="h-5 w-5" />
              </span>
              <div>
                <p className="font-medium">Informasi pembayaran</p>
                <p className="text-sm text-muted-foreground">
                  Isi sesuai informasi dari pelanggan.
                </p>
              </div>
            </div>
            <div className="mb-5 flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => fillSample("150000")}>Isi contoh sesuai</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => fillSample("150001")}>Isi contoh selisih</Button>
            </div>
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="reference">Nomor referensi</Label>
                <Input
                  id="reference"
                  required
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  placeholder="Contoh: PJP-DEMO-0001"
                  className="h-12 font-technical"
                />
                <p className="text-xs text-muted-foreground">
                  Biasanya tercantum pada detail transaksi atau notifikasi
                  pembayaran.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="amount">Nominal yang dibayarkan</Label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-medium text-muted-foreground">
                    Rp
                  </span>
                  <Input
                    id="amount"
                    required
                    min={1}
                    type="number"
                    inputMode="numeric"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    placeholder="350000"
                    className="h-12 pl-11 text-base font-medium"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="order">
                  Nomor pesanan{" "}
                  <span className="font-normal text-muted-foreground">
                    (opsional)
                  </span>
                </Label>
                <Input
                  id="order"
                  value={order}
                  onChange={(event) => setOrder(event.target.value)}
                  placeholder="Contoh: ORD-DEMO-001"
                  className="h-12 font-technical"
                />
              </div>
              <div className="rounded-xl bg-secondary px-4 py-3 text-sm">
                <span className="text-muted-foreground">Outlet aktif</span>
                <span className="ml-2 font-medium">
                  {outlets.data?.items[0]?.name ?? "Memuat outlet…"}
                </span>
              </div>
              {error && (
                <p
                  role="alert"
                  className="rounded-xl border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger"
                >
                  {error}
                </p>
              )}
              <Button disabled={loading} className="h-12 w-full text-[15px]">
                {loading ? (
                  <InlineLoader label="Memeriksa pembayaran…" />
                ) : (
                  "Periksa pembayaran"
                )}
              </Button>
            </div>
          </form>
          <aside className="rounded-xl border bg-secondary/65 p-5">
            <p className="font-medium">Sebelum memeriksa</p>
            <ol className="mt-4 space-y-4 text-sm text-muted-foreground">
              <li className="flex gap-3">
                <Step number="1" />
                Jangan jadikan screenshot sebagai satu-satunya bukti.
              </li>
              <li className="flex gap-3">
                <Step number="2" />
                Masukkan nominal yang benar-benar dibayar.
              </li>
              <li className="flex gap-3">
                <Step number="3" />
                Tunggu hasil sebelum menyerahkan pesanan.
              </li>
            </ol>
          </aside>
        </div>
      ) : (
        <CheckResult
          result={result}
          enteredAmount={Number(amount)}
          onReset={reset}
        />
      )}
    </div>
  );
}

function CheckResult({
  result,
  enteredAmount,
  onReset,
}: {
  result: Result;
  enteredAmount: number;
  onReset: () => void;
}) {
  const decision = paymentDecision({
    found: result.found,
    providerStatus: result.provider_status,
    callbackReceived: result.payment?.callback_received,
    amountMatch: result.amount_match,
    orderMatch: result.order_match,
    riskLevel: result.risk_result.risk_level,
    recommendationCode: result.risk_result.recommendation_code,
  });
  const safe = decision.canProcess;
  return (
    <div className="space-y-5">
      <DecisionBanner
        level={decision.risk}
        title={decision.label}
        message={decision.message}
        action={
          safe && result.payment ? (
            <Button asChild>
              <Link href={`/dashboard/payments/${result.payment.id}`}>
                Buka detail pembayaran
              </Link>
            </Button>
          ) : (
            <Button onClick={onReset}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Coba lagi
            </Button>
          )
        }
        secondary={
          !safe && result.payment ? (
            <Button asChild variant="outline">
              <Link href={`/dashboard/payments/${result.payment.id}`}>
                Tinjau detail
              </Link>
            </Button>
          ) : undefined
        }
      />
      {result.found && result.payment && (
        <AmountComparison
          expected={result.payment.expected_amount ?? null}
          paid={result.payment.amount ?? enteredAmount}
          submitted={enteredAmount}
          currency={result.payment.currency ?? "IDR"}
        />
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <section className="rounded-xl border bg-card p-5">
          <h2 className="font-medium">Mengapa hasilnya demikian?</h2>
          <ul className="mt-4 space-y-3">
            {splitReasons(result.risk_result.reasons).map((reason) => (
              <li
                key={reason}
                className="flex gap-2.5 text-sm leading-6 text-muted-foreground"
              >
                {safe ? (
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-success" />
                ) : (
                  <ShieldAlert className="mt-1 h-4 w-4 shrink-0 text-danger" />
                )}
                {reason}
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-xl border bg-card px-5">
          <DetailList
            items={[
              { label: "Ditemukan", value: result.found ? "Ya" : "Belum" },
              {
                label: "Status penyedia",
                value:
                  result.provider_status === "success"
                    ? "Berhasil"
                    : result.provider_status === "not_found"
                      ? "Tidak ditemukan"
                      : result.provider_status,
              },
              {
                label: "Konfirmasi pembayaran",
                value: result.payment?.callback_received
                  ? "Tercatat"
                  : "Belum tercatat",
              },
              {
                label: "Nominal",
                value: result.amount_match ? "Sesuai" : "Tidak sesuai",
              },
              ...(result.order_match == null
                ? []
                : [
                    {
                      label: "Pesanan",
                      value: result.order_match ? "Sesuai" : "Tidak sesuai",
                    },
                  ]),
            ]}
          />
        </section>
      </div>
      <AIAnalysisCard
        score={result.risk_result.final_score}
        confidence={result.risk_result.confidence_score}
        reasons={result.risk_result.reasons}
        mode={result.risk_result.analysis_mode}
      />
      <GnnScoreSummary
        score={result.risk_result.gnn_score}
        weight={result.risk_result.gnn_final_weight}
        legacyScore={result.risk_result.legacy_ensemble_score}
        modelVersion={result.risk_result.gnn_metadata?.model_version}
        fallbackReason={result.risk_result.gnn_metadata?.fallback_reason}
      />
      <p className="text-center text-xs leading-5 text-muted-foreground">
        {result.demo_notice}
      </p>
    </div>
  );
}

function Step({ number }: { number: string }) {
  return (
    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-card text-xs font-bold text-primary shadow-sm">
      {number}
    </span>
  );
}
