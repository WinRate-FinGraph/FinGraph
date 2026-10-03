import { z } from "zod";

export const loginSchema = z.object({
    email: z
        .string()
        .min(1, "Email wajib diisi")
        .email("Format email tidak valid"),
    password: z
        .string()
        .min(1, "Kata sandi wajib diisi")
        .max(72, "Kata sandi maksimal 72 karakter"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
    full_name: z.string().min(2, "Nama wajib diisi").max(120),
    email: z.string().min(1, "Email wajib diisi").email("Format email tidak valid"),
    password: z.string().min(12, "Kata sandi minimal 12 karakter").max(72, "Kata sandi maksimal 72 karakter"),
    confirm_password: z.string().min(12, "Konfirmasi kata sandi wajib diisi").max(72, "Konfirmasi kata sandi maksimal 72 karakter"),
    role: z.literal("merchant"),
    institution_name: z.string().max(120).optional().or(z.literal("")),
}).refine((value) => value.password === value.confirm_password, {
    path: ["confirm_password"],
    message: "Konfirmasi kata sandi tidak sama",
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
