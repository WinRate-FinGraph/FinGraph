"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AppLogo } from "@/components/layout/app-logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { registerUser } from "@/lib/auth";
import { isDemoBuild } from "@/lib/runtime";
import { registerSchema, type RegisterFormValues } from "@/lib/validations/auth";

export default function RegisterPage() {
    const router = useRouter();
    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<RegisterFormValues>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            full_name: "",
            email: "",
            password: "",
            confirm_password: "",
            role: "merchant",
            institution_name: "",
        },
    });

    async function onSubmit(values: RegisterFormValues) {
        try {
            await registerUser({
                full_name: values.full_name,
                email: values.email,
                password: values.password,
                role: values.role,
                institution_name: values.institution_name || null,
            });
            toast.success("Akun berhasil dibuat. Silakan masuk.");
            router.push("/login");
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Gagal mendaftar");
        }
    }

    if (!isDemoBuild) {
        return (
            <main className="min-h-screen bg-background text-foreground">
                <header className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-6">
                    <AppLogo />
                    <Button asChild variant="ghost"><Link href="/login">Masuk</Link></Button>
                </header>
                <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-2xl items-center px-4 py-12 md:px-6">
                    <Card className="w-full rounded-xl border bg-card surface-raised">
                        <CardContent className="p-7 md:p-10">
                            <h1 className="text-2xl font-medium tracking-[-.035em]">Pendaftaran mandiri tidak tersedia</h1>
                            <p className="mt-3 leading-7 text-muted-foreground">Hubungi administrator FinGraph untuk pembuatan akun dan pengaturan akses usaha.</p>
                            <Button asChild className="mt-7"><Link href="/login">Kembali ke halaman masuk</Link></Button>
                        </CardContent>
                    </Card>
                </section>
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-background text-foreground">
            <header className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-6">
                <AppLogo />
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                    <Button asChild variant="ghost" className="rounded-md">
                        <Link href="/login">Masuk</Link>
                    </Button>
                </div>
            </header>

            <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-10 px-4 py-10 md:px-6 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="hidden lg:block">
                    <p className="text-sm font-medium text-primary">Daftar usaha</p>
                    <h1 className="mt-4 text-4xl font-medium tracking-[-.04em]">
                        Buat akun FinGraph
                    </h1>
                    <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
                        Buat akun usaha untuk Mode Demo. Akun analyst dan admin hanya dibuat melalui akun demo lokal.
                    </p>
                </div>

                <Card className="mx-auto w-full max-w-xl rounded-xl border bg-card surface-raised">
                    <CardContent className="p-6 md:p-8">
                        <h2 className="text-2xl font-medium tracking-[-.035em]">Daftar usaha</h2>
                        <p className="mt-2 text-sm text-muted-foreground">Daftarkan usaha untuk mencoba pemeriksaan pembayaran QRIS.</p>

                        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 grid gap-5">
                            <div className="space-y-2">
                                <Label htmlFor="full_name">Nama pemilik</Label>
                                <Input id="full_name" placeholder="Nama pemilik usaha" {...register("full_name")} />
                                {errors.full_name && <p className="text-sm text-red-600 dark:text-red-300">{errors.full_name.message}</p>}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="email">Email</Label>
                                <Input id="email" type="email" placeholder="pemilik@usaha.id" {...register("email")} />
                                {errors.email && <p className="text-sm text-red-600 dark:text-red-300">{errors.email.message}</p>}
                            </div>

                            <div className="grid gap-5 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="password">Kata sandi</Label>
                                    <Input id="password" type="password" placeholder="Minimal 12 karakter" {...register("password")} />
                                    {errors.password && <p className="text-sm text-red-600 dark:text-red-300">{errors.password.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="confirm_password">Konfirmasi kata sandi</Label>
                                    <Input id="confirm_password" type="password" placeholder="Ulangi kata sandi" {...register("confirm_password")} />
                                    {errors.confirm_password && <p className="text-sm text-red-600 dark:text-red-300">{errors.confirm_password.message}</p>}
                                </div>
                            </div>

                            <div className="grid gap-5 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="role">Peran</Label>
                                    <Input id="role" value="Merchant UMKM" disabled />
                                    <input type="hidden" value="merchant" {...register("role")} />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="institution_name">Nama usaha</Label>
                                <Input id="institution_name" placeholder="Contoh: Koperasi Nusantara" {...register("institution_name")} />
                            </div>

                            <Button type="submit" disabled={isSubmitting} className="h-12">
                                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Daftar
                            </Button>
                        </form>

                        <p className="mt-6 text-center text-sm text-muted-foreground">
                            Sudah punya akun? <Link href="/login" className="font-medium text-primary hover:underline">Masuk</Link>
                        </p>
                    </CardContent>
                </Card>
            </section>
        </main>
    );
}
