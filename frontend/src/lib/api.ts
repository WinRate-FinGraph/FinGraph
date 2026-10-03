const API_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "/api/v1";

export type ApiError = {
    detail?: string;
    message?: string;
};

export async function apiFetch<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const token =
        typeof window !== "undefined" ? localStorage.getItem("fingraph_token") : null;

    const headers = new Headers(options.headers);

    if (!headers.has("Content-Type") && options.body) {
        headers.set("Content-Type", "application/json");
    }

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = (await response.json().catch(() => ({}))) as ApiError;
        if (response.status === 401 && typeof window !== "undefined") {
            localStorage.removeItem("fingraph_token");
            localStorage.removeItem("fingraph_user");
        }
        throw new Error(error.detail || error.message || `Permintaan gagal (${response.status})`);
    }

    return response.json() as Promise<T>;
}

export const apiUrl = API_URL;

export async function downloadWithAuth(path: string, filename: string) {
    const token = localStorage.getItem("fingraph_token");
    const response = await fetch(`${API_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!response.ok) throw new Error("Gagal mengunduh laporan");
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}
