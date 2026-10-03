"use client";

import {
  AlertCircle,
  BrainCircuit,
  BellRing,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Loader2,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  alertStatusPresentation,
  normalizeRisk,
  orderStatusPresentation,
  paymentStatusPresentation,
  profileStatusPresentation,
  riskPresentation,
  splitReasons,
  type PresentationTone,
} from "@/lib/presentation";

const toneStyles: Record<PresentationTone, string> = {
  success: "border-success/25 bg-success-soft text-success",
  warning: "border-warning/25 bg-warning-soft text-warning",
  danger: "border-danger/25 bg-danger-soft text-danger",
  info: "border-info/25 bg-info-soft text-info",
  neutral: "border-border bg-surface-subtle text-foreground",
};

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-[26px] font-medium leading-tight tracking-[-.035em] sm:text-[30px]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  );
}

export function StatusBadge({
  kind = "risk",
  value,
  className,
}: {
  kind?: "risk" | "payment" | "order" | "alert" | "profile";
  value: string;
  className?: string;
}) {
  const item =
    kind === "risk"
      ? riskPresentation[normalizeRisk(value)]
      : kind === "payment"
        ? paymentStatusPresentation[value]
        : kind === "order"
          ? orderStatusPresentation[value]
          : kind === "profile"
            ? profileStatusPresentation[value]
            : alertStatusPresentation[value];
  const resolved = item ?? {
    label: value.replaceAll("_", " "),
    tone: "neutral" as const,
  };
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium leading-none",
        toneStyles[resolved.tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {resolved.label}
    </span>
  );
}

export function SummaryStrip({
  items,
}: {
  items: {
    label: string;
    value: React.ReactNode;
    hint?: string;
    tone?: PresentationTone;
  }[];
}) {
  const compact = items.length <= 3;
  return (
    <section
      className={cn(
        "grid overflow-hidden rounded-xl border border-border bg-surface",
        compact ? "grid-cols-3" : "grid-cols-2 lg:grid-cols-4",
      )}
      aria-label="Ringkasan"
    >
      <>
        {items.map((item, index) => (
          <div
            key={item.label}
            className={cn(
              "min-h-[88px] px-4 py-3.5 sm:px-5",
              compact
                ? index > 0 && "border-l border-border"
                : index > 0 &&
                    "border-t border-border sm:border-l sm:border-t-0",
              !compact && index > 1 && "sm:border-t lg:border-t-0",
            )}
          >
            <p className="text-[13px] font-medium text-muted-foreground">
              {item.label}
            </p>
            <p
              className={cn(
                "mt-1 text-[22px] font-medium tracking-[-.035em]",
                item.tone === "success" && "text-success",
                item.tone === "warning" && "text-warning",
                item.tone === "danger" && "text-danger",
              )}
            >
              {item.value}
            </p>
            {item.hint && (
              <p className="mt-0.5 text-xs text-muted-foreground">
                {item.hint}
              </p>
            )}
          </div>
        ))}
      </>
    </section>
  );
}

export function DecisionBanner({
  level,
  title,
  message,
  action,
  secondary,
}: {
  level: string;
  title: string;
  message: string;
  action?: React.ReactNode;
  secondary?: React.ReactNode;
}) {
  const risk = normalizeRisk(level);
  const tone = riskPresentation[risk].tone;
  const Icon =
    risk === "low" ? CheckCircle2 : risk === "medium" ? BellRing : ShieldAlert;
  return (
    <section className={cn("rounded-xl border p-5", toneStyles[tone])}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3.5">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-surface-raised">
            <Icon className="h-5 w-5" />
          </span>
          <div>
            <StatusBadge value={risk} />
            <h2 className="mt-2.5 text-xl font-medium tracking-[-.025em]">
              {title}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 opacity-90">
              {message}
            </p>
          </div>
        </div>
        {(action || secondary) && (
          <div className="flex shrink-0 flex-wrap gap-2 sm:justify-end">
            {action}
            {secondary}
          </div>
        )}
      </div>
    </section>
  );
}

export function AIAnalysisCard({
  score,
  confidence,
  reasons,
  mode,
}: {
  score: number;
  confidence?: number | null;
  reasons?: string[] | string | null;
  mode?: "ensemble_ai" | "ensemble_gnn" | "rule_graph_fallback";
}) {
  const boundedScore = Math.max(0, Math.min(score, 1));
  const boundedConfidence =
    confidence == null ? null : Math.max(0, Math.min(confidence, 1));
  const topReason = splitReasons(reasons)[0];
  const risk = normalizeRisk(
    boundedScore >= 0.7 ? "high" : boundedScore >= 0.4 ? "medium" : "low",
  );
  const tone = riskPresentation[risk].tone;
  const bar =
    tone === "danger"
      ? "bg-danger"
      : tone === "warning"
        ? "bg-warning"
        : "bg-success";
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="flex flex-col gap-4 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-accent-foreground">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-medium">Analisis FinGraph</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {mode === "ensemble_gnn"
                ? "Pola pembayaran, riwayat transaksi, dan aturan keamanan"
                : mode === "ensemble_ai"
                  ? "Riwayat pembayaran dan aturan FinGraph"
                  : "Pemeriksaan pembayaran dan aturan FinGraph"}
            </p>
          </div>
        </div>
        <StatusBadge value={risk} />
      </div>
      <div className="grid sm:grid-cols-2">
        <div className="p-5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Skor risiko</p>
              <p className="mt-1 text-[30px] font-medium tracking-[-.04em]">
                {Math.round(boundedScore * 100)}
                <span className="ml-1 text-sm font-normal text-muted-foreground">/100</span>
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              Semakin tinggi, semakin perlu ditinjau
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-subtle">
            <div className={cn("h-full rounded-full", bar)} style={{ width: `${boundedScore * 100}%` }} />
          </div>
        </div>
        <div className="border-t border-border p-5 sm:border-l sm:border-t-0">
          <p className="text-sm text-muted-foreground">Keyakinan hasil</p>
          <p className="mt-1 text-[30px] font-medium tracking-[-.04em]">
            {boundedConfidence == null
              ? "—"
              : `${Math.round(boundedConfidence * 100)}%`}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            Seberapa cocok hasil pemeriksaan yang tersedia. Bukan jaminan transaksi bebas penipuan.
          </p>
        </div>
      </div>
      {topReason && (
        <div className="border-t border-border bg-surface-subtle px-5 py-3 text-sm">
          <span className="font-medium">Alasan utama:</span>{" "}
          <span className="text-muted-foreground">{topReason}</span>
        </div>
      )}
    </section>
  );
}

export function GnnScoreSummary({
  score,
  weight,
  legacyScore,
  modelVersion,
  fallbackReason,
}: {
  score?: number | null;
  weight?: number;
  legacyScore?: number | null;
  modelVersion?: string | null;
  fallbackReason?: string | null;
}) {
  const active = score != null && (weight ?? 0) > 0;
  const fallbackMessage =
    fallbackReason === "qris_graphsage_artifact_missing"
      ? "Pemeriksaan pola belum tersedia; hasil memakai pemeriksaan lain."
      : fallbackReason === "qris_graphsage_inference_failed"
        ? "Pemeriksaan pola belum selesai; hasil memakai pemeriksaan lain."
        : fallbackReason === "disabled"
        ? "Pemeriksaan pola dinonaktifkan; hasil memakai pemeriksaan lain."
        : "Pemeriksaan pola tidak dipakai untuk pembayaran ini.";
  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-medium">Pemeriksaan pola pembayaran</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {active
              ? "Pola pembayaran ikut diperiksa; hasil ini bukan satu-satunya dasar keputusan."
              : fallbackMessage}
          </p>
        </div>
        <StatusBadge kind="profile" value={active ? "active" : "inactive"} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-muted/40 p-3">
          <p className="text-xs text-muted-foreground">Nilai pola</p>
          <p className="mt-1 font-medium">{score == null ? "Tidak digunakan" : `${Math.round(score * 100)}/100`}</p>
        </div>
        <div className="rounded-lg bg-muted/40 p-3">
          <p className="text-xs text-muted-foreground">Pengaruh ke hasil</p>
          <p className="mt-1 font-medium">{active ? `${Math.round((weight ?? 0) * 100)}%` : "0%"}</p>
        </div>
        <div className="rounded-lg bg-muted/40 p-3">
          <p className="text-xs text-muted-foreground">Pemeriksaan lain</p>
          <p className="mt-1 font-medium">{legacyScore == null ? "—" : `${Math.round(legacyScore * 100)}/100`}</p>
        </div>
      </div>
      {active && modelVersion && (
        <p className="mt-3 truncate text-xs text-muted-foreground">Model: <span className="font-technical">{modelVersion}</span></p>
      )}
      <p className="mt-2 text-xs text-muted-foreground">Aturan keamanan dapat membuat hasil pemeriksaan menjadi lebih tinggi.</p>
    </section>
  );
}

export function AIAnalysisInline({
  score,
  confidence,
}: {
  score: number;
  confidence?: number | null;
}) {
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
      <span>Risiko {Math.round(Math.max(0, Math.min(score, 1)) * 100)}/100</span>
      <span aria-hidden>·</span>
      <span>
        Keyakinan {confidence == null ? "—" : `${Math.round(Math.max(0, Math.min(confidence, 1)) * 100)}%`}
      </span>
    </span>
  );
}

export function LoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div
      className="overflow-hidden rounded-xl border bg-card"
      aria-label="Memuat data"
    >
      <div className="space-y-0">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="flex items-center gap-4 border-b p-5 last:border-0"
          >
            <Skeleton className="h-10 w-10 rounded-xl" />
            <div className="flex-1">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-2 h-3 w-64 max-w-full" />
            </div>
            <Skeleton className="h-7 w-24 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title = "Belum ada data",
  description = "Informasi akan muncul setelah aktivitas pertama diproses.",
  action,
  icon: Icon = Inbox,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex min-h-60 flex-col items-center justify-center rounded-xl border border-dashed bg-card px-6 py-10 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-xl bg-secondary text-muted-foreground">
        <Icon className="h-5 w-5" />
      </span>
      <h2 className="mt-4 font-medium">{title}</h2>
      <p className="mt-1.5 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex min-h-60 flex-col items-center justify-center rounded-xl border border-danger/25 bg-danger-soft px-6 py-10 text-center">
      <AlertCircle className="h-7 w-7 text-danger" />
      <h2 className="mt-3 font-medium">Data belum dapat dimuat</h2>
      <p className="mt-1.5 max-w-md text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-5">
          <RefreshCw className="mr-2 h-4 w-4" />
          Coba lagi
        </Button>
      )}
    </div>
  );
}

export function DataState({
  loading,
  error,
  empty,
  onRetry,
  children,
  emptyTitle,
  emptyDescription,
}: {
  loading: boolean;
  error?: string | null;
  empty?: boolean;
  onRetry?: () => void;
  children: React.ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (empty)
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  return <>{children}</>;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Cari referensi…",
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">Cari</span>
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-11 bg-card pl-10"
      />
    </label>
  );
}

export function FilterBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-3 sm:flex-row sm:items-center">
      {children}
    </div>
  );
}

export function AmountComparison({
  expected,
  paid,
  submitted,
  currency = "IDR",
}: {
  expected: number | null;
  paid: number;
  submitted?: number | null;
  currency?: string;
}) {
  const formatter = new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });
  const difference = submitted == null ? paid - (expected ?? paid) : submitted - paid;
  const matched = submitted == null && expected == null ? true : Math.abs(difference) < 1;
  return (
    <section className="overflow-hidden rounded-xl border bg-card">
      <div className={cn("grid", submitted == null ? "sm:grid-cols-3" : "sm:grid-cols-2 lg:grid-cols-4")}>
        <DetailMetric
          label="Nilai pesanan"
          value={
            expected == null ? "Belum dihubungkan" : formatter.format(expected)
          }
        />
        <DetailMetric
          label={submitted == null ? "Nominal pembayaran" : "Nominal yang dimasukkan"}
          value={formatter.format(submitted ?? paid)}
          bordered
        />
        {submitted != null && <DetailMetric
          label="Nominal pembayaran"
          value={formatter.format(paid)}
          bordered
        />}
        <DetailMetric
          label={submitted == null ? "Selisih dari pesanan" : "Selisih nominal"}
          value={formatter.format(difference)}
          bordered
          tone={matched ? "success" : "danger"}
        />
      </div>
    </section>
  );
}

function DetailMetric({
  label,
  value,
  bordered,
  tone,
}: {
  label: string;
  value: string;
  bordered?: boolean;
  tone?: PresentationTone;
}) {
  return (
    <div
      className={cn("p-5", bordered && "border-t sm:border-l sm:border-t-0")}
    >
      <p className="text-sm text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-2 text-xl font-medium tracking-[-.025em]",
          tone === "success" && "text-success",
          tone === "danger" && "text-danger",
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function DetailList({
  items,
}: {
  items: { label: string; value: React.ReactNode; mono?: boolean }[];
}) {
  return (
    <dl className="divide-y">
      {items.map((item) => (
        <div
          key={item.label}
          className="grid gap-1 py-3.5 sm:grid-cols-[170px_1fr] sm:gap-6"
        >
          <dt className="text-sm text-muted-foreground">{item.label}</dt>
          <dd
            className={cn(
              "break-words text-sm font-medium sm:text-right",
              item.mono && "font-technical text-xs",
            )}
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ActivityTimeline({
  items,
}: {
  items: { label: string; at: string; description?: string }[];
}) {
  return (
    <ol className="space-y-0">
      {items.map((item) => (
        <li
          key={`${item.label}-${item.at}`}
          className="relative grid grid-cols-[22px_1fr] gap-3 pb-5 last:pb-0"
        >
          <span className="relative mt-1.5 h-2.5 w-2.5 rounded-full bg-primary after:absolute after:left-[4px] after:top-3 after:h-[calc(100%+12px)] after:w-px after:bg-border last:after:hidden" />
          <div>
            <p className="text-sm font-medium">{item.label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{item.at}</p>
            {item.description && (
              <p className="mt-1 text-sm text-muted-foreground">
                {item.description}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

export function AdvancedAnalysis({ children }: { children: React.ReactNode }) {
  return (
    <Collapsible>
      <div className="rounded-xl border bg-card">
        <CollapsibleTrigger className="flex min-h-14 w-full items-center justify-between px-5 text-left text-sm font-medium">
          <span>Lihat analisis teknis</span>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </CollapsibleTrigger>
        <CollapsibleContent className="border-t px-5 py-1">
          {children}
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

export function DemoModeBanner() {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-info/25 bg-info-soft px-4 py-3 text-sm text-info">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        <strong>Mode Demo.</strong> Konfirmasi pembayaran berasal dari
        simulator, bukan jaringan QRIS atau PJP nyata.
      </p>
    </div>
  );
}

export function ChartCard({
  title,
  description,
  children,
  summary,
  className,
  contentClassName,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  summary: string;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <section className={cn("rounded-xl border bg-card p-5 surface-raised", className)}>
      <div>
        <h2 className="font-medium">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      <div className={cn("mt-5", contentClassName)}>{children}</div>
      <p className="sr-only">{summary}</p>
    </section>
  );
}

export function InlineLoader({ label = "Memproses" }: { label?: string }) {
  return (
    <span className="inline-flex items-center">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      {label}
    </span>
  );
}

export function PaginationBar({
  total,
  limit,
  offset,
  onPageChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
}) {
  if (total <= limit && offset === 0) return null;
  const start = total ? offset + 1 : 0;
  const end = Math.min(offset + limit, total);
  return (
    <nav
      className="flex flex-col gap-3 rounded-xl border border-border bg-surface px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      aria-label="Navigasi halaman"
    >
      <p className="text-sm text-muted-foreground">
        <strong className="text-foreground">
          {start}–{end}
        </strong>{" "}
        dari {total}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={offset === 0}
          onClick={() => onPageChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Sebelumnya
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={offset + limit >= total}
          onClick={() => onPageChange(offset + limit)}
        >
          Berikutnya
          <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </nav>
  );
}
