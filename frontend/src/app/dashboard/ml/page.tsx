"use client";

import { useEffect, useState, type FormEvent } from "react";
import { BrainCircuit, DatabaseZap, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import {
  DataState,
  DetailList,
  EmptyState,
  PageHeader,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { getStoredUser } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";

type Model = {
  dataset_name?: string;
  model_name?: string;
  model_family?: string;
  version?: string;
  created_at?: string;
  sample_count?: number;
  dataset_rows?: number;
  roc_auc?: number;
  pr_auc?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  split_strategy?: string;
  split_warning?: string | null;
  test_warning?: string | null;
  threshold?: number;
  seed?: number;
  test?: Record<string, unknown>;
  baseline_test?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
};
type Adaptive = {
  qris: {
    labels_available: number;
    usable_binary_labels: number;
    labels_required: number;
    ready_for_training: boolean;
    class_distribution: Record<string, number>;
  };
};
type GraphStatus = {
  prototype: boolean;
  qris_enabled: boolean;
  qris_scoring_active?: boolean;
  gnn_final_weight?: number;
  model_available: boolean;
  active_model?: Model | null;
  active_job?: GraphJob | null;
  recent_jobs?: GraphJob[];
  candidates?: Model[];
  fallback: string;
  note: string;
};
type GraphJob = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  attempts?: number;
  created_at?: string;
  finished_at?: string | null;
  parameters?: Record<string, number>;
  progress?: {
    phase?: string;
    epoch?: number;
    epochs?: number;
    train_loss?: number;
    validation_pr_auc?: number;
    best_validation_pr_auc?: number;
    best_epoch?: number;
    elapsed_seconds?: number;
  };
  result?: {
    version?: string;
    auto_promoted?: boolean;
    auto_promotion_reason?: string;
    metrics?: {
      epochs?: number;
      best_epoch?: number;
      train?: Record<string, unknown>;
      validation?: Record<string, unknown>;
      test?: Record<string, unknown>;
      baseline_test?: Record<string, unknown>;
      dataset_rows?: number;
      split_strategy?: string;
      threshold?: number;
      seed?: number;
      split_warning?: string | null;
      test_warning?: string | null;
    };
  } | null;
  error?: string | null;
};
type GnnParameters = Record<"limit_rows" | "epochs" | "hidden_dim" | "learning_rate" | "dropout" | "weight_decay" | "patience" | "seed", string>;

const DEFAULT_GNN_PARAMETERS: GnnParameters = {
  limit_rows: "50000",
  epochs: "10",
  hidden_dim: "64",
  learning_rate: "0.003",
  dropout: "0.2",
  weight_decay: "0.0001",
  patience: "5",
  seed: "42",
};

const GNN_FIELDS: { key: keyof GnnParameters; label: string; min: string; max: string; step: string }[] = [
  { key: "limit_rows", label: "Maks. baris", min: "4", max: "100000", step: "1" },
  { key: "epochs", label: "Epoch", min: "1", max: "100", step: "1" },
  { key: "hidden_dim", label: "Hidden dim", min: "16", max: "128", step: "1" },
  { key: "learning_rate", label: "Learning rate", min: "0.00001", max: "0.01", step: "any" },
  { key: "dropout", label: "Dropout", min: "0", max: "0.6", step: "any" },
  { key: "weight_decay", label: "Weight decay", min: "0", max: "0.01", step: "any" },
  { key: "patience", label: "Patience", min: "1", max: "10", step: "1" },
  { key: "seed", label: "Seed", min: "0", max: "2147483647", step: "1" },
];

function metricText(metrics: Record<string, unknown> | undefined, key: string) {
  const value = metrics?.[key];
  return typeof value === "number" ? value.toFixed(3) : "—";
}
export default function ModelsPage() {
  const user = getStoredUser();
  const models = useApi<{ items: Model[] }>("/ml/models");
  const adaptive = useApi<Adaptive>("/ml/adaptive/status");
  const graph = useApi<GraphStatus>("/ml/graphsage/status");
  const reloadGraph = graph.reload;
  const [training, setTraining] = useState("");
  const [graphParameters, setGraphParameters] = useState(DEFAULT_GNN_PARAMETERS);
  const [graphJob, setGraphJob] = useState<GraphJob | null>(null);
  const [jobPollError, setJobPollError] = useState("");
  const pollJobId = graphJob?.job_id ?? graph.data?.active_job?.job_id;
  const pollJobStatus = graphJob?.status ?? graph.data?.active_job?.status;
  async function train(kind: "qris" | "adaptive") {
    setTraining(kind);
    try {
      await apiFetch(
        kind === "qris"
          ? "/ml/train/qris-tabular"
          : "/ml/adaptive/qris-retrain",
        { method: "POST" },
      );
      toast.success(
        kind === "qris"
          ? "Model QRIS selesai dilatih"
          : "Model adaptive selesai dilatih",
      );
      await Promise.all([models.reload(), adaptive.reload(), graph.reload()]);
    } catch (reason) {
      toast.error(
        reason instanceof Error
          ? reason.message
          : "Training belum dapat dijalankan",
      );
    } finally {
      setTraining("");
    }
  }
  useEffect(() => {
    if (!pollJobId || !["queued", "running"].includes(pollJobStatus ?? "")) return;
    let alive = true;
    let timer: number;
    const poll = async () => {
      try {
        const updated = await apiFetch<GraphJob>(`/ml/graphsage/jobs/${pollJobId}`);
        if (!alive) return;
        setGraphJob(updated);
        setJobPollError("");
        if (["completed", "failed"].includes(updated.status)) {
          void reloadGraph();
          if (updated.status === "completed") {
            toast.success(updated.result?.auto_promoted
              ? "Training selesai; model pertama lolos baseline dan aktif otomatis"
              : "Training GraphSAGE selesai; periksa hasil sebelum promosi");
          }
          else toast.error(updated.error || "Training GraphSAGE gagal");
        }
      } catch (reason) {
        if (alive) setJobPollError(reason instanceof Error ? reason.message : "Status training gagal dimuat");
      }
      if (alive) timer = window.setTimeout(poll, 2000);
    };
    timer = window.setTimeout(poll, 500);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [pollJobId, pollJobStatus, reloadGraph]);

  async function startGraphSage(parameters: GnnParameters) {
    setTraining("graphsage");
    setJobPollError("");
    try {
      const query = new URLSearchParams(Object.entries(parameters));
      const job = await apiFetch<GraphJob>(`/ml/train/qris-graphsage?${query}`, { method: "POST" });
      setGraphJob(job);
      toast.success("Training GraphSAGE masuk antrean");
      void graph.reload();
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "Training GraphSAGE gagal dimulai");
    } finally {
      setTraining("");
    }
  }

  function trainGraphSage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void startGraphSage(graphParameters);
  }

  async function promoteGraphModel(version: string) {
    try {
      await apiFetch(`/ml/graphsage/${encodeURIComponent(version)}/promote`, { method: "POST" });
      toast.success("Model GraphSAGE aktif");
      await graph.reload();
    } catch (reason) {
      toast.error(reason instanceof Error ? reason.message : "Promosi model gagal");
    }
  }
  const latest = models.data?.items[0];
  const graphIsActive = graph.data?.qris_scoring_active ?? (graph.data?.model_available && graph.data?.qris_enabled);
  const gnnFinalWeight = graph.data?.gnn_final_weight ?? 0.5;
  const activeGraphVersion = graph.data?.active_model?.version;
  const displayedJob = graphJob ?? graph.data?.active_job ?? graph.data?.recent_jobs?.[0] ?? null;
  const priorJobs = graph.data?.recent_jobs?.filter((job) => job.job_id !== displayedJob?.job_id) ?? [];
  const graphMetrics = displayedJob?.result?.metrics;
  const evaluation = graphMetrics ?? graph.data?.active_model ?? undefined;
  const testMetrics = evaluation?.test as Record<string, unknown> | undefined;
  const baselineMetrics = evaluation?.baseline_test as Record<string, unknown> | undefined;
  const confusion = testMetrics?.confusion as Record<string, unknown> | undefined;
  const classCounts = testMetrics?.class_counts as Record<string, unknown> | undefined;
  const allPositive = Number(confusion?.true_negative ?? 0) === 0 && Number(confusion?.false_negative ?? 0) === 0 && Number(confusion?.false_positive ?? 0) > 0 && Number(confusion?.true_positive ?? 0) > 0;
  const evaluationCards = [
    { label: "GraphSAGE test", metrics: testMetrics },
    { label: "Feature-only baseline", metrics: baselineMetrics },
  ];
  return (
    <div className="space-y-6">
      <PageHeader
        title="Model"
        description="Lihat hasil model yang membantu menilai pembayaran dan atur model GraphSAGE."
        action={
          <Button
            variant="outline"
            onClick={() => {
              void models.reload();
              void adaptive.reload();
              void graph.reload();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Muat ulang
          </Button>
        }
      />
      <DataState
        loading={models.loading || adaptive.loading || graph.loading}
        error={models.error || adaptive.error || graph.error}
        onRetry={models.reload}
      >
        {models.data && adaptive.data && graph.data && (
          <>
            <SummaryStrip
              items={[
                { label: "Model tersimpan", value: models.data.items.length },
                {
                  label: "Label tersedia",
                  value: adaptive.data.qris.labels_available,
                },
                {
                  label: "Siap adaptive",
                  value: adaptive.data.qris.ready_for_training ? "Ya" : "Belum",
                  tone: adaptive.data.qris.ready_for_training
                    ? "success"
                    : "warning",
                },
                {
                  label: "GraphSAGE",
                  value: graphIsActive ? "Digunakan" : "Fallback",
                  tone: graphIsActive ? "success" : "warning",
                },
              ]}
            />
            <section className="rounded-xl border bg-card p-5">
              <h2 className="font-medium">Cara kerja model</h2>
              <ol className="mt-4 grid gap-2 sm:grid-cols-5">
                {[
                  ["1. Data", "Data contoh"],
                  ["2. Latih", "Buat model"],
                  ["3. Cek", "Bandingkan hasil"],
                  ["4. Pilih", "Aktifkan model"],
                  ["5. Pakai", "Bantu menilai pembayaran"],
                ].map(([step, detail]) => (
                  <li key={step} className="rounded-lg border bg-secondary/40 p-3 text-sm">
                    <span className="font-medium">{step}</span>
                    <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
                  </li>
                ))}
              </ol>
            </section>
            <div className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
              <section className="overflow-hidden rounded-xl border bg-card">
                <div className="flex items-center justify-between border-b px-5 py-4">
                  <div>
                    <h2 className="font-medium">Daftar model</h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Artifact lokal dan metadata training
                    </p>
                  </div>
                  <BrainCircuit className="h-5 w-5 text-primary" />
                </div>
                {models.data.items.length ? (
                  <div className="divide-y">
                    {models.data.items.map((model, index) => (
                      <article
                        key={`${model.version}-${index}`}
                        className="grid gap-4 px-5 py-4 md:grid-cols-[1fr_140px_150px]"
                      >
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium">
                              {model.model_name ||
                                model.model_family ||
                                "Model FinGraph"}
                            </p>
                            <StatusBadge
                              kind="payment"
                              value={
                                model.dataset_name === "qris_graph"
                                  ? model.version === activeGraphVersion ? "success" : "pending"
                                  : index === 0 ? "success" : "pending"
                              }
                            />
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {model.dataset_name || "Dataset internal"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">
                            Sampel
                          </p>
                          <p className="mt-1 font-technical text-xs">
                            {model.sample_count ?? model.dataset_rows ?? "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Versi</p>
                          <p className="mt-1 truncate font-technical text-xs">
                            {model.version || "—"}
                          </p>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="Belum ada model tersimpan"
                    description="Pemeriksaan tetap memakai aturan dan pemeriksaan pola yang tersedia."
                  />
                )}
              </section>
              <div className="space-y-6">
                <section className="rounded-xl border bg-card p-5">
                  <h2 className="font-medium">Pembelajaran dari catatan</h2>
                  <div className="mt-4">
                    <DetailList
                      items={[
                        {
                          label: "Label valid",
                          value: String(
                            adaptive.data.qris.usable_binary_labels,
                          ),
                        },
                        {
                          label: "Minimum",
                          value: String(adaptive.data.qris.labels_required),
                        },
                        {
                          label: "Fraud",
                          value: String(
                            adaptive.data.qris.class_distribution.fraud ?? 0,
                          ),
                        },
                        {
                          label: "Legitimate",
                          value: String(
                            adaptive.data.qris.class_distribution.legitimate ??
                              0,
                          ),
                        },
                      ]}
                    />
                  </div>
                  {user?.role === "admin" && (
                    <div className="mt-4 grid gap-2">
                      <Button
                        onClick={() => train("qris")}
                        disabled={Boolean(training)}
                      >
                        <DatabaseZap className="mr-2 h-4 w-4" />
                        {training === "qris" ? "Melatih…" : "Latih model QRIS"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => train("adaptive")}
                        disabled={
                          Boolean(training) ||
                          !adaptive.data.qris.ready_for_training
                        }
                      >
                        {training === "adaptive"
                          ? "Melatih…"
                          : "Latih dari catatan"}
                      </Button>
                    </div>
                  )}
                </section>
                {latest?.created_at && (
                  <p className="text-xs text-muted-foreground">
                    Model terbaru: {formatDateTime(latest.created_at)}
                  </p>
                )}
              </div>
            </div>
            <section className="space-y-5 rounded-xl border bg-card p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-medium">Pemeriksaan pola pembayaran</h2>
                  <p className="mt-1 max-w-3xl text-sm text-muted-foreground">Model melihat hubungan pada riwayat pembayaran untuk membantu pemeriksaan. Hasil ini bukan bukti tunggal penipuan.</p>
                </div>
                <StatusBadge kind="profile" value={graphIsActive ? "active" : "inactive"} />
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Status penilaian</p>
                  <p className="mt-1 font-medium">{graphIsActive ? "Model sedang digunakan" : "Memakai pemeriksaan lain"}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{graph.data.qris_enabled ? "Pemeriksaan pola dinyalakan" : "Pemeriksaan pola dimatikan"}{!graph.data.model_available ? " · belum ada model aktif" : ""}</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Kontribusi yang berlaku</p>
                  <p className="mt-1 font-medium">{graphIsActive ? `${Math.round(gnnFinalWeight * 100)}% GraphSAGE · ${Math.round((1 - gnnFinalWeight) * 100)}% ensemble lama` : `0% saat ini · target ${Math.round(gnnFinalWeight * 100)}% saat model aktif`}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Aturan tertentu dapat membuat hasil akhir menjadi lebih tinggi.</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Model yang dipakai</p>
                  <p className="mt-1 truncate font-technical text-xs">{graph.data.active_model?.version || "Belum ada model aktif"}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{graphIsActive ? "Versi aktif untuk scoring" : `Fallback: ${graph.data.fallback === "legacy_ensemble" ? "ensemble lama (aturan, model tabular, heuristik graf, adaptif)" : graph.data.fallback}`}</p>
                </div>
              </div>
              <p className="rounded-lg border border-warning/30 bg-warning-soft px-4 py-3 text-xs leading-5 text-muted-foreground">Data yang dipakai masih berupa contoh. Hasil pengujian belum membuktikan ketepatan pada transaksi QRIS nyata.</p>

              {evaluation && (
                <div className="grid gap-4 lg:grid-cols-[.8fr_1.2fr]">
                  <section className="rounded-lg border p-4">
                    <h3 className="font-medium">Hasil pengujian</h3>
                    <DetailList items={[
                      { label: "Dataset", value: "Generated QRIS benchmark" },
                      { label: "Baris", value: String(evaluation.dataset_rows ?? graph.data.active_model?.dataset_rows ?? "—") },
                      { label: "Split", value: evaluation.split_strategy ?? graph.data.active_model?.split_strategy ?? "Temporal" },
                      { label: "Seed", value: String(evaluation.seed ?? graph.data.active_model?.seed ?? "—") },
                      { label: "Legitimate test", value: String(classCounts?.legitimate ?? "—") },
                      { label: "Fraud scenario test", value: String(classCounts?.fraud_scenario ?? "—") },
                    ]} />
                  </section>
                  <section className="rounded-lg border p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-medium">Hasil pada batas nilai {evaluation.threshold ?? graph.data.active_model?.threshold ?? 0.5}</h3>
                      {allPositive && <StatusBadge value="high" />}
                    </div>
                    {allPositive && <p className="mt-3 rounded-md bg-danger-soft p-3 text-sm text-danger">Peringatan: model menandai semua data uji sebagai berisiko. Nilai tinggi ini belum berarti hasilnya baik.</p>}
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {evaluationCards.map(({ label, metrics }) => (
                        <div key={label} className="rounded-md bg-muted/40 p-3 text-xs">
                          <p className="mb-2 font-medium">{label}</p>
                          <p>PR-AUC {metricText(metrics, "pr_auc")} · ROC-AUC {metricText(metrics, "roc_auc")}</p>
                          <p className="mt-1">Precision {metricText(metrics, "precision")} · Recall {metricText(metrics, "recall")} · F1 {metricText(metrics, "f1")}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                      {[["TN", confusion?.true_negative], ["FP", confusion?.false_positive], ["FN", confusion?.false_negative], ["TP", confusion?.true_positive]].map(([label, value]) => (
                        <div key={String(label)} className="rounded-md border p-2"><p className="text-muted-foreground">{String(label)}</p><p className="mt-1 font-technical font-medium">{String(value ?? "—")}</p></div>
                      ))}
                    </div>
                  </section>
                </div>
              )}

              {displayedJob && (
                <div className="rounded-lg border p-4" aria-live="polite">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">Pelatihan: {displayedJob.status}</p>
                    <p className="text-xs text-muted-foreground">{displayedJob.progress?.phase?.replaceAll("_", " ") || "menunggu"} · attempt {displayedJob.attempts ?? 0} · {displayedJob.progress?.elapsed_seconds ?? 0}s</p>
                  </div>
                  {displayedJob.status === "running" && (
                    <p className="mt-2 text-sm text-muted-foreground">
                      Epoch {displayedJob.progress?.epoch ?? 0}/{displayedJob.progress?.epochs ?? displayedJob.parameters?.epochs ?? "—"}
                      {typeof displayedJob.progress?.train_loss === "number" && ` · loss ${displayedJob.progress.train_loss.toFixed(4)}`}
                      {typeof displayedJob.progress?.validation_pr_auc === "number" && ` · val PR-AUC ${displayedJob.progress.validation_pr_auc.toFixed(3)}`}
                      {typeof displayedJob.progress?.best_epoch === "number" && ` · best epoch ${displayedJob.progress.best_epoch}`}
                    </p>
                  )}
                  {jobPollError && <p className="mt-2 text-xs text-destructive">{jobPollError}; mencoba lagi.</p>}
                  {displayedJob.error && <p className="mt-2 text-sm text-destructive">{displayedJob.error}</p>}
                  {displayedJob.status === "completed" && displayedJob.result?.auto_promoted && (
                    <p className="mt-2 rounded-md bg-success-soft px-3 py-2 text-sm text-success">Model pertama sudah melewati hasil pembanding dan diaktifkan otomatis.</p>
                  )}
                  {displayedJob.status === "completed" && displayedJob.result && !displayedJob.result.auto_promoted && displayedJob.result.auto_promotion_reason !== "active_model_exists" && (
                    <p className="mt-2 rounded-md bg-warning-soft px-3 py-2 text-sm text-muted-foreground">Model belum diaktifkan otomatis. Admin dapat memeriksa dan memilih model ini.</p>
                  )}
                  {graphMetrics && <p className="mt-3 text-xs text-muted-foreground">Settings: {Object.entries(displayedJob.parameters || {}).map(([key, value]) => `${key}=${value}`).join(" · ")} · best epoch {graphMetrics.best_epoch ?? "—"}/{graphMetrics.epochs ?? "—"}</p>}
                </div>
              )}

              {user?.role === "admin" && (
                <section className="space-y-3 rounded-lg border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="font-medium">Latih model</h3>
                      <p className="mt-1 text-xs text-muted-foreground">Gunakan pengaturan standar, lalu periksa hasilnya sebelum mengaktifkan model.</p>
                    </div>
                    <Button onClick={() => void startGraphSage(DEFAULT_GNN_PARAMETERS)} disabled={training === "graphsage" || Boolean(displayedJob && ["queued", "running"].includes(displayedJob.status))}>
                      <DatabaseZap className="mr-2 h-4 w-4" />
                      {training === "graphsage" ? "Menyiapkan…" : "Latih dengan pengaturan standar"}
                    </Button>
                  </div>
                  <details className="rounded-lg border p-4">
                  <summary className="cursor-pointer text-sm font-medium">Pengaturan lanjutan</summary>
                  <form className="mt-4 space-y-4" onSubmit={trainGraphSage}>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {GNN_FIELDS.map((field) => (
                        <div key={field.key} className="space-y-1.5">
                          <Label htmlFor={`gnn-${field.key}`}>{field.label}</Label>
                          <Input
                            id={`gnn-${field.key}`}
                            type="number"
                            min={field.min}
                            max={field.max}
                            step={field.step}
                            required
                            value={graphParameters[field.key]}
                            onChange={(event) => setGraphParameters((current) => ({ ...current, [field.key]: event.target.value }))}
                          />
                        </div>
                      ))}
                    </div>
                    <Button type="submit" disabled={training === "graphsage" || Boolean(displayedJob && ["queued", "running"].includes(displayedJob.status))}>
                      {training === "graphsage" || displayedJob?.status === "queued" || displayedJob?.status === "running" ? "Training berjalan…" : "Mulai training GraphSAGE"}
                    </Button>
                  </form>
                  </details>
                </section>
              )}

              {Boolean(graph.data.candidates?.length) && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium">Kandidat tersimpan</h3>
                  {graph.data.candidates?.map((candidate) => (
                    <div key={candidate.version} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-technical text-xs">{candidate.version}</p>
                        <p className="mt-1 text-xs text-muted-foreground">Test PR-AUC {metricText(candidate.test, "pr_auc")} · baseline {metricText(candidate.baseline_test, "pr_auc")}</p>
                      </div>
                      {user?.role === "admin" && candidate.version && (
                        <Button size="sm" variant="outline" onClick={() => void promoteGraphModel(candidate.version!)}>Promosikan</Button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {priorJobs.length > 0 && (
                <details className="rounded-lg border p-4">
                  <summary className="cursor-pointer text-sm font-medium">Riwayat retraining ({priorJobs.length})</summary>
                  <div className="mt-3 divide-y">
                    {priorJobs.map((job) => (
                      <div key={job.job_id} className="py-3 text-xs">
                        <p className="font-medium">{job.status} · {job.created_at ? formatDateTime(job.created_at) : job.job_id} · attempt {job.attempts ?? 0}</p>
                        {job.result?.metrics && <p className="mt-1 text-muted-foreground">Test PR-AUC {metricText(job.result.metrics.test, "pr_auc")} · baseline {metricText(job.result.metrics.baseline_test, "pr_auc")} · best epoch {job.result.metrics.best_epoch ?? "—"}</p>}
                        {job.error && <p className="mt-1 text-destructive">{job.error}</p>}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </section>
          </>
        )}
      </DataState>
    </div>
  );
}
