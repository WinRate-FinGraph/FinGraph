export type PlanCode = "basic" | "growth" | "premium";

export type PlanDefinition = {
  code: PlanCode;
  name: string;
  price: number;
  audience: string;
  summary: string;
  transactionLimit: number;
  outletLimit: number | null;
  seatLimit: number;
  support: string;
  featured?: boolean;
  features: string[];
};

export const planCatalog: PlanDefinition[] = [
  {
    code: "basic",
    name: "Basic",
    price: 49_000,
    audience: "Untuk usaha kecil dan satu outlet",
    summary: "Ruang kerja sederhana untuk mulai membaca pembayaran usaha.",
    transactionLimit: 500,
    outletLimit: 1,
    seatLimit: 1,
    support: "Email dan pusat bantuan",
    features: [
      "Ringkasan pembayaran dan hasil pemeriksaan",
      "Ringkasan usaha dengan informasi penting",
      "Peringatan saat ada hal yang perlu dilihat",
      "Saran langkah berikutnya",
      "Riwayat pembayaran dan catatan manual",
      "1 akun usaha dan 1 outlet",
    ],
  },
  {
    code: "growth",
    name: "Growth",
    price: 99_000,
    audience: "Untuk tim kecil dan beberapa outlet",
    summary: "Bekerja bersama tim saat usaha mulai berkembang.",
    transactionLimit: 2_000,
    outletLimit: 3,
    seatLimit: 3,
    support: "Prioritas melalui WhatsApp/chat",
    featured: true,
    features: [
      "Semua fitur Basic",
      "Ringkasan berdasarkan periode, outlet, dan prioritas",
      "Hingga 3 outlet dan 3 akun pengguna",
      "Kelompokkan dan tandai transaksi",
      "Laporan dan unduh data",
      "Catatan tindakan bersama",
    ],
  },
  {
    code: "premium",
    name: "Premium",
    price: 149_000,
    audience: "Untuk banyak outlet dan tim yang lebih besar",
    summary: "Bantuan pemeriksaan yang lebih luas saat usaha terus berkembang.",
    transactionLimit: 5_000,
    outletLimit: null,
    seatLimit: 5,
    support: "Dedicated onboarding dan video call",
    features: [
      "Semua fitur Growth",
      "5+ akun termasuk akses pengelola",
      "Pantau aktivitas dan riwayat tindakan tim",
      "Lihat pola pembayaran di banyak outlet",
      "Bandingkan pembayaran lintas wilayah",
      "Berbagi pembelajaran tanpa membagikan data mentah",
      "Hubungkan dengan sistem usaha lain",
    ],
  },
];

const planRank: Record<PlanCode, number> = { basic: 0, growth: 1, premium: 2 };

export function normalizePlan(value?: string | null): PlanCode {
  return value === "growth" || value === "premium" ? value : "basic";
}

export function planAtLeast(current: PlanCode, required: PlanCode) {
  return planRank[current] >= planRank[required];
}

export function planByCode(code: PlanCode) {
  return planCatalog.find((plan) => plan.code === code) ?? planCatalog[0];
}

export function formatPlanPrice(value: number) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function requiredPlanForPath(path: string): PlanCode {
  if (
    path.startsWith("/dashboard/graph") ||
    path.startsWith("/dashboard/cross-border") ||
    path.startsWith("/dashboard/federated") ||
    path.startsWith("/dashboard/admin-monitoring") ||
    path.startsWith("/dashboard/risk-config") ||
    path.startsWith("/dashboard/simulation")
  ) {
    return "premium";
  }
  if (
    path.startsWith("/dashboard/reports") ||
    path.startsWith("/dashboard/audit-logs")
  ) {
    return "growth";
  }
  return "basic";
}
