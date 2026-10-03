"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { LockKeyhole, Monitor, QrCode, Store } from "lucide-react";
import { toast } from "sonner";
import { DataState, PageHeader } from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";

type Profile = {
  name: string;
  business_type: string;
  owner_name: string;
  phone: string | null;
  address: string;
  city: string;
  province: string;
};

export default function SettingsPage() {
  const query = useApi<Profile>("/merchants/me");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (
      query.data &&
      new URLSearchParams(window.location.search).get("tab") === "appearance"
    ) {
      const trigger = [
        ...document.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
      ].find((item) => item.textContent?.includes("Tampilan"));
      trigger?.click();
    }
  }, [query.data]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      await apiFetch("/merchants/me", {
        method: "PUT",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      toast.success("Profil usaha diperbarui");
      setDirty(false);
      await query.reload();
    } catch (reason) {
      toast.error(
        reason instanceof Error ? reason.message : "Perubahan belum tersimpan",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Pengaturan Usaha"
        description="Kelola informasi usaha, QRIS, tampilan, dan keamanan akun."
      />
      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {query.data && (
          <Tabs
            defaultValue="profile"
            className="grid gap-6 md:grid-cols-[210px_1fr]"
          >
            <TabsList className="h-fit flex-col items-stretch rounded-xl bg-card p-2">
              <TabsTrigger value="profile" className="min-h-11 justify-start">
                <Store className="mr-2 h-4 w-4" />
                Profil Usaha
              </TabsTrigger>
              <TabsTrigger value="outlets" className="min-h-11 justify-start">
                <Store className="mr-2 h-4 w-4" />
                Outlet
              </TabsTrigger>
              <TabsTrigger value="qris" className="min-h-11 justify-start">
                <QrCode className="mr-2 h-4 w-4" />
                QRIS
              </TabsTrigger>
              <TabsTrigger
                value="appearance"
                className="min-h-11 justify-start"
              >
                <Monitor className="mr-2 h-4 w-4" />
                Tampilan
              </TabsTrigger>
              <TabsTrigger value="security" className="min-h-11 justify-start">
                <LockKeyhole className="mr-2 h-4 w-4" />
                Keamanan
              </TabsTrigger>
            </TabsList>
            <div>
              <TabsContent value="profile">
                <form
                  onSubmit={save}
                  onInput={() => setDirty(true)}
                  className="overflow-hidden rounded-xl border bg-card"
                >
                  <div className="border-b px-5 py-4">
                    <h2 className="font-medium">Profil Usaha</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Informasi yang digunakan pada dashboard merchant.
                    </p>
                  </div>
                  <div className="grid gap-5 p-5 sm:grid-cols-2">
                    {[
                      ["name", "Nama usaha"],
                      ["business_type", "Jenis usaha"],
                      ["owner_name", "Nama pemilik"],
                      ["phone", "Nomor telepon"],
                      ["address", "Alamat usaha"],
                      ["city", "Kota"],
                      ["province", "Provinsi"],
                    ].map(([name, label]) => (
                      <div
                        key={name}
                        className={
                          name === "address"
                            ? "space-y-2 sm:col-span-2"
                            : "space-y-2"
                        }
                      >
                        <Label htmlFor={name}>{label}</Label>
                        <Input
                          id={name}
                          name={name}
                          defaultValue={String(
                            query.data?.[name as keyof Profile] ?? "",
                          )}
                          className="h-11"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between border-t bg-secondary/50 px-5 py-4">
                    <p className="text-xs text-muted-foreground">
                      {dirty
                        ? "Ada perubahan yang belum disimpan."
                        : "Semua perubahan sudah tersimpan."}
                    </p>
                    <Button disabled={!dirty || saving}>
                      {saving ? "Menyimpan…" : "Simpan perubahan"}
                    </Button>
                  </div>
                </form>
              </TabsContent>
              <TabsContent value="outlets">
                <SettingsLink
                  title="Kelola outlet"
                  description="Lihat outlet yang terhubung dengan profil QRIS."
                  href="/dashboard/qris"
                />
              </TabsContent>
              <TabsContent value="qris">
                <SettingsLink
                  title="QRIS dan pencairan dana"
                  description="Periksa identitas QRIS dan rekening pencairan tersamarkan."
                  href="/dashboard/qris"
                />
              </TabsContent>
              <TabsContent value="appearance">
                <section className="rounded-xl border bg-card p-5">
                  <h2 className="font-medium">Tampilan</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Tema terang digunakan sebagai default untuk keterbacaan
                    kasir dan pemilik usaha.
                  </p>
                  <div className="mt-5 flex items-center justify-between rounded-xl bg-secondary p-4">
                    <span className="text-sm font-medium">Ubah tema</span>
                    <ThemeToggle />
                  </div>
                </section>
              </TabsContent>
              <TabsContent value="security">
                <section className="rounded-xl border bg-card p-5">
                  <h2 className="font-medium">Keamanan akun</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Gunakan kata sandi unik dan jangan bagikan token login.
                    Penggantian kata sandi mandiri belum tersedia pada Mode
                    Demo.
                  </p>
                </section>
              </TabsContent>
            </div>
          </Tabs>
        )}
      </DataState>
    </div>
  );
}

function SettingsLink({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="font-medium">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      <Button asChild className="mt-5">
        <Link href={href}>Buka pengelolaan</Link>
      </Button>
    </section>
  );
}
