import { JAKARTA_TIMEZONE, parseApiDate } from "@/lib/presentation";

export function formatCurrency(value: number, currency = "IDR") {
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
    }).format(value);
}

export function formatDateTime(value: string) {
    return new Intl.DateTimeFormat("id-ID", {
        timeZone: JAKARTA_TIMEZONE,
        dateStyle: "medium",
        timeStyle: "short",
    }).format(parseApiDate(value));
}

export function formatTime(value: string) {
    return new Intl.DateTimeFormat("id-ID", { timeZone: JAKARTA_TIMEZONE, hour: "2-digit", minute: "2-digit" }).format(parseApiDate(value));
}

export function formatShortDate(value: string) {
    return new Intl.DateTimeFormat("id-ID", { timeZone: JAKARTA_TIMEZONE, day: "numeric", month: "short" }).format(parseApiDate(value));
}

export function greetingForJakarta(now = new Date()) {
    const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: JAKARTA_TIMEZONE, hour: "2-digit", hourCycle: "h23" }).format(now));
    if (hour < 11) return "Selamat pagi";
    if (hour < 15) return "Selamat siang";
    if (hour < 18) return "Selamat sore";
    return "Selamat malam";
}

export function compactId(value: string, start = 8, end = 6) {
    if (!value) return "-";
    if (value.length <= start + end) return value;
    return `${value.slice(0, start)}...${value.slice(-end)}`;
}
