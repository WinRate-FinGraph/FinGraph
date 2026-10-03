import { apiFetch } from "@/lib/api";
import type { PlanCode } from "@/lib/plans";

export type User = {
    id: string;
    full_name: string;
    email: string;
    role: "admin" | "analyst" | "merchant";
    institution_name?: string | null;
    merchant_id?: string | null;
    subscription_plan: PlanCode;
    subscription?: {
        code: PlanCode;
        name: string;
        monthly_price: number;
        transaction_limit: number;
        outlet_limit: number | null;
        seat_limit: number;
    };
};

export type LoginResponse = {
    access_token: string;
    token_type: string;
    user: User;
};

export type RegisterResponse = User;

export async function registerUser(payload: {
    full_name: string;
    email: string;
    password: string;
    role: User["role"];
    institution_name?: string | null;
}) {
    return apiFetch<RegisterResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function login(email: string, password: string) {
    const result = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });

    localStorage.setItem("fingraph_token", result.access_token);
    localStorage.setItem("fingraph_user", JSON.stringify(result.user));

    return result;
}

export function logout() {
    localStorage.removeItem("fingraph_token");
    localStorage.removeItem("fingraph_user");
    window.location.href = "/login";
}

export function getStoredUser(): User | null {
    if (typeof window === "undefined") return null;

    const raw = localStorage.getItem("fingraph_user");
    if (!raw) return null;

    try {
        const user = JSON.parse(raw) as User;
        user.role = user.role.toLowerCase() as User["role"];
        return user;
    } catch {
        return null;
    }
}

export function getToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("fingraph_token");
}
