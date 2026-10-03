"use client";

import { FormEvent, useState } from "react";
import { Building2, CheckCircle2, ChevronDown, QrCode } from "lucide-react";
import { toast } from "sonner";
import {
  DataState,
  DetailList,
  PageHeader,
  StatusBadge,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { humanizeQrisType } from "@/lib/presentation";

type Profile = {
  id: string;
  nmid: string;
  outlet_name: string;
  qris_type: string;
  acquirer_name: string;
  masked_settlement_account: string;
  status: string;
  last_verified_at: string | null;
  verification_notice: string;
};
type VerifyResult = {
  status: "valid" | "mismatch" | "unknown";
  reasons: string[];
  notice: string;
};

export default function QrisPage() {
  const profiles = useApi<{ items: Profile[]; demo_notice: string }>(
    "/merchants/qris-profiles",
  );
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [checking, setChecking] = useState(false);
  const selectedProfile = profiles.data?.items.find(
    (item) => item.id === selected,
  );

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setChecking(true);
    try {
      setResult(
        await apiFetch("/merchants/qris-profiles/verify", {
          method: "POST",
          body: JSON.stringify({
            qris_profile_id: selected || null,
            payload: form.get("payload"),
          }),
        }),
      );
      toast.success("QRIS selesai dibandingkan");
      await profiles.reload();
    } catch (reason) {
      toast.error(
        reason instanceof Error ? reason.message : "QRIS belum dapat diperiksa",
      );
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="QRIS dan Outlet"
        description="Kelola profil QRIS yang digunakan oleh setiap outlet usaha."
      />
      <DataState
        loading={profiles.loading}
        error={profiles.error}
        empty={profiles.data?.items.length === 0}
        onRetry={profiles.reload}
      >
        {profiles.data && (
          <>
            <div className="grid gap-5 lg:grid-cols-[.7fr_1.3fr]">
              <section className="rounded-xl bg-primary p-6 text-primary-foreground shadow-sm">
                <div className="flex items-start justify-between">
                  <span className="grid h-12 w-12 place-items-center rounded-xl bg-primary-foreground/10">
                    <QrCode className="h-6 w-6" />
                  </span>
                  <span className="rounded-full bg-primary-foreground/10 px-2.5 py-1 text-xs font-medium">
                    Mode Demo
                  </span>
                </div>
                <p className="mt-10 text-sm opacity-70">
                  Profil QRIS tersimpan
                </p>
                <p className="mt-1 text-2xl font-medium tracking-[-.03em]">
                  {profiles.data.items.length} outlet
                </p>
                <p className="mt-5 text-sm leading-6 opacity-75">
                FinGraph membandingkan data usaha, outlet, dan QRIS,
                  dan penyedia dengan profil tersimpan.
                </p>
              </section>
              <section className="overflow-hidden rounded-xl border bg-card">
                <div className="border-b px-5 py-4">
                  <h2 className="font-medium">Profil tersimpan</h2>
                </div>
                <div className="divide-y">
                  {profiles.data.items.map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      aria-pressed={selected === profile.id}
                      onClick={() => {
                        setSelected(profile.id);
                        setResult(null);
                      }}
                      className={
                        selected === profile.id
                          ? "flex min-h-24 w-full items-center gap-4 bg-accent/60 px-5 py-4 text-left"
                          : "flex min-h-24 w-full items-center gap-4 px-5 py-4 text-left hover:bg-secondary/50"
                      }
                    >
                      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-secondary text-primary">
                        <Building2 className="h-5 w-5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center justify-between gap-2">
                          <strong className="truncate text-sm">
                            {profile.outlet_name}
                          </strong>
                          <StatusBadge kind="profile" value={profile.status} />
                        </span>
                        <span className="mt-1 block font-technical text-xs text-muted-foreground">
                          {maskIdentifier(profile.nmid)}
                        </span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {humanizeQrisType(profile.qris_type)} ·{" "}
                          {profile.acquirer_name}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            </div>
            {selectedProfile && (
              <section className="rounded-xl border bg-card p-5 sm:p-6">
                <div>
                  <h2 className="font-medium">Detail profil</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {selectedProfile.outlet_name}
                  </p>
                </div>
                <div className="mt-4">
                  <DetailList items={profileDetails(selectedProfile)} />
                </div>
                <Collapsible className="mt-5 border-t pt-4">
                  <CollapsibleTrigger className="flex min-h-11 w-full items-center justify-between text-left text-sm font-medium">
                    <span>Opsi lanjutan: periksa payload QRIS</span>
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="mt-3 rounded-xl bg-secondary p-4">
                      <p className="text-sm leading-6 text-muted-foreground">
                  FinGraph akan mencocokkan QR ini dengan profil yang
                        tersimpan pada Mode Demo. Unggah atau scan belum
                        tersedia karena decoder gambar belum diaktifkan.
                      </p>
                      <form onSubmit={verify} className="mt-4 space-y-3">
                        <Label htmlFor="payload">Payload hasil decode</Label>
                        <Textarea
                          id="payload"
                          name="payload"
                          required
                          minLength={6}
                          maxLength={4096}
                          placeholder="Tempel payload hanya jika Anda memahami data QR yang digunakan"
                          className="min-h-28 bg-card font-technical text-xs"
                        />
                        <Button disabled={checking}>
                          {checking ? "Memeriksa…" : "Bandingkan dengan profil"}
                        </Button>
                      </form>
                      {result && (
                        <div
                          role="status"
                          className={
                            result.status === "valid"
                              ? "mt-4 rounded-xl border border-success/25 bg-success-soft p-4"
                              : "mt-4 rounded-xl border border-warning/25 bg-warning-soft p-4"
                          }
                        >
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4" />
                            <p className="font-medium">
                              {result.status === "valid"
                                ? "QRIS sesuai profil"
                                : result.status === "mismatch"
                                  ? "Ada data yang tidak sesuai"
                                  : "QRIS belum dikenal"}
                            </p>
                          </div>
                          {result.reasons.map((reason) => (
                            <p
                              key={reason}
                              className="mt-2 text-sm text-muted-foreground"
                            >
                              {reason}
                            </p>
                          ))}
                          <p className="mt-3 text-xs text-muted-foreground">
                            {result.notice}
                          </p>
                        </div>
                      )}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </section>
            )}
          </>
        )}
      </DataState>
    </div>
  );
}

function maskIdentifier(value: string) {
  return value.length < 8
    ? value
    : `${value.slice(0, 5)}••••${value.slice(-4)}`;
}
function profileDetails(profile: Profile) {
  return [
    { label: "Nama outlet", value: profile.outlet_name },
    { label: "NMID simulasi", value: maskIdentifier(profile.nmid), mono: true },
    { label: "Jenis QRIS", value: humanizeQrisType(profile.qris_type) },
    { label: "Penyedia pembayaran", value: profile.acquirer_name },
    {
      label: "Rekening pencairan",
      value: profile.masked_settlement_account,
      mono: true,
    },
    {
      label: "Terakhir diperiksa",
      value: profile.last_verified_at
        ? formatDateTime(profile.last_verified_at)
        : "Belum pernah",
    },
  ];
}
