"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, ReceiptText, Store, UserRound } from "lucide-react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { AppLogo } from "@/components/layout/app-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/auth";
import { isDemoBuild } from "@/lib/runtime";
import { loginSchema, type LoginFormValues } from "@/lib/validations/auth";
import { PlanBadge } from "@/components/product/pricing";

const demoPassword = "password123";
const demoAccounts = [
  { role: "merchant", label: "Merchant", description: "Cek pembayaran", email: "merchant@fingraph.id", icon: Store },
  { role: "analyst", label: "Analyst", description: "Periksa risiko", email: "analyst@fingraph.id", icon: UserRound },
  { role: "admin", label: "Admin", description: "Atur demo", email: "admin@fingraph.id", icon: UserRound },
];

export default function LoginPage() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: isDemoBuild ? "merchant@fingraph.id" : "",
      password: isDemoBuild ? demoPassword : "",
    },
  });
  const selected = useWatch({ control, name: "email" });

  useEffect(() => {
    const role = new URLSearchParams(window.location.search).get("role");
    const account = demoAccounts.find((item) => item.role === role);
    if (isDemoBuild && account) {
      setValue("email", account.email);
      setValue("password", demoPassword);
    }
  }, [setValue]);

  async function onSubmit(values: LoginFormValues) {
    try {
      await login(values.email, values.password);
      toast.success("Selamat datang kembali");
      router.push("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Belum dapat masuk");
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="mx-auto flex h-[68px] max-w-[1160px] items-center justify-between px-4 sm:px-6">
        <AppLogo />
        <Button asChild variant="ghost">
          <Link href="/">Kembali</Link>
        </Button>
      </header>
      <section className="mx-auto grid max-w-[1160px] items-center gap-10 px-4 py-8 sm:px-6 lg:min-h-[calc(100vh-68px)] lg:grid-cols-[.9fr_1.1fr] lg:py-12">
        <div className="hidden lg:block">
          <span className="grid h-12 w-12 place-items-center rounded-xl bg-accent text-primary">
            <ReceiptText className="h-6 w-6" />
          </span>
          <h1 className="mt-6 max-w-md text-[38px] font-medium leading-tight tracking-[-.045em]">
            Pembayaran jelas, usaha lebih tenang.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-7 text-muted-foreground">
            Masuk untuk memeriksa pembayaran, menangani peringatan, atau membuka
            ruang investigasi.
          </p>
        </div>
        <div className="mx-auto w-full max-w-[520px] rounded-xl border bg-card p-5 surface-raised sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-medium tracking-[-.035em]">
              Masuk ke FinGraph
            </h2>
            {isDemoBuild && <PlanBadge plan="premium" />}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {isDemoBuild
              ? "Semua akun demo memakai paket Premium agar seluruh alur dapat diperagakan."
              : "Gunakan akun yang diberikan administrator."}
          </p>
          {isDemoBuild && (
            <div className="mt-6 grid grid-cols-3 gap-2">
              {demoAccounts.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => {
                    setValue("email", account.email);
                    setValue("password", demoPassword);
                  }}
                  aria-pressed={selected === account.email}
                  className={
                    selected === account.email
                      ? "flex min-h-32 flex-col items-center justify-center gap-1.5 rounded-xl border border-primary bg-accent px-2 text-xs font-medium text-primary"
                      : "flex min-h-32 flex-col items-center justify-center gap-1.5 rounded-xl border bg-card px-2 text-xs font-medium text-muted-foreground hover:bg-secondary"
                  }
                >
                  <account.icon className="h-4 w-4" />
                  <span>{account.label}</span>
                  <span className="text-[10px] font-normal">{account.description}</span>
                  <span className="mt-1 w-full truncate text-left text-[10px] font-normal text-muted-foreground" title={account.email}>
                    Email: {account.email}
                  </span>
                  <span className="w-full truncate text-left text-[10px] font-normal text-muted-foreground">
                    Kata sandi: {demoPassword}
                  </span>
                </button>
              ))}
            </div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                className="h-12"
                {...register("email")}
              />
              {errors.email && (
                <p role="alert" className="text-sm text-destructive">
                  {errors.email.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Kata sandi</Label>
              <Input
                id="password"
                type="password"
                className="h-12"
                {...register("password")}
              />
              {errors.password && (
                <p role="alert" className="text-sm text-destructive">
                  {errors.password.message}
                </p>
              )}
            </div>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-12 w-full text-[15px]"
            >
              {isSubmitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Masuk
            </Button>
          </form>
          {isDemoBuild && (
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Belum punya akun merchant?{" "}
              <Link
                href="/register"
                className="font-medium text-primary hover:underline"
              >
                Daftar usaha
              </Link>
            </p>
          )}
          {isDemoBuild && (
            <p className="mt-4 text-center text-xs leading-5 text-muted-foreground">
              Kredensial demo hanya untuk penggunaan lokal.
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
