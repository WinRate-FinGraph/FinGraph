import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { canAccessDashboardPath, dashboardHomeForRole } from "../src/lib/access.ts";
import { alertStatusPresentation, consistentRecommendation, isJakartaToday, orderStatusPresentation, parseApiDate, paymentDecision, riskPresentation, splitReasons } from "../src/lib/presentation.ts";

test("status merchant selalu menggunakan Bahasa Indonesia", () => {
  assert.equal(riskPresentation.low.label, "Risiko rendah");
  assert.equal(riskPresentation.medium.label, "Perlu diperiksa");
  assert.equal(orderStatusPresentation.awaiting_payment.label, "Menunggu pembayaran");
  assert.equal(alertStatusPresentation.open.label, "Butuh tindakan");
});

test("rekomendasi aman tidak dapat berubah menjadi hold atau report", () => {
  assert.equal(consistentRecommendation("low", "REPORT_AND_HOLD").code, "APPROVE");
  assert.equal(consistentRecommendation("medium", "REPORT_AND_HOLD").code, "VERIFY");
  assert.equal(consistentRecommendation("high", "APPROVE").code, "DO_NOT_RELEASE_GOODS");
});

test("alasan semicolon dipisahkan menjadi butir yang mudah dibaca", () => {
  assert.deepEqual(splitReasons("Nominal tidak sesuai; Callback belum diterima"), ["Nominal tidak sesuai", "Callback belum diterima"]);
});

test("tanggal hari ini dihitung dalam zona Asia/Jakarta", () => {
  const now = new Date("2026-07-15T00:30:00+07:00");
  assert.equal(isJakartaToday("2026-07-14T17:10:00Z", now), true);
  assert.equal(isJakartaToday("2026-07-14T16:59:00Z", now), false);
});

test("timestamp UTC tanpa suffix tetap dibaca sebagai UTC", () => {
  assert.equal(parseApiDate("2026-07-14T17:10:00").toISOString(), "2026-07-14T17:10:00.000Z");
});

test("status pembayaran non-sukses tidak pernah menghasilkan tindakan aman", () => {
  assert.equal(paymentDecision({ providerStatus: "refunded", riskLevel: "low", recommendationCode: "APPROVE" }).risk, "high");
  assert.equal(paymentDecision({ providerStatus: "pending", riskLevel: "low", recommendationCode: "APPROVE" }).code, "VERIFY");
});

test("pembayaran hanya dapat diproses saat semua fakta utama sesuai", () => {
  assert.equal(paymentDecision({ providerStatus: "success", callbackReceived: true, amountMatch: true, orderMatch: true, riskLevel: "low" }).canProcess, true);
  assert.equal(paymentDecision({ providerStatus: "success", callbackReceived: true, amountMatch: false, riskLevel: "low" }).code, "HOLD");
  assert.equal(paymentDecision({ providerStatus: "success", callbackReceived: false, amountMatch: true, riskLevel: "low" }).canProcess, false);
  assert.equal(paymentDecision({ found: false, providerStatus: "not_found", riskLevel: "low" }).code, "DO_NOT_RELEASE_GOODS");
});

test("route merchant dan analyst dibatasi oleh shell", () => {
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/graph"), false);
  assert.equal(canAccessDashboardPath("analyst", "/dashboard/payments/check"), true);
  assert.equal(canAccessDashboardPath("analyst", "/dashboard/risk-config"), false);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/payments/abc"), true);
  assert.equal(canAccessDashboardPath("admin", "/dashboard/simulation"), true);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/admin-monitoring"), false);
  assert.equal(canAccessDashboardPath("analyst", "/dashboard/admin-monitoring"), false);
  assert.equal(canAccessDashboardPath("admin", "/dashboard/admin-monitoring"), true);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/reports", "basic"), false);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/reports", "growth"), true);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/audit-logs", "growth"), true);
  assert.equal(canAccessDashboardPath("merchant", "/dashboard/graph", "premium"), false);
});

test("dashboard utama merchant, analyst, dan admin berbeda", () => {
  assert.equal(dashboardHomeForRole("merchant"), "merchant-home");
  assert.equal(dashboardHomeForRole("analyst"), "analyst-home");
  assert.equal(dashboardHomeForRole("admin"), "admin-home");
  assert.equal(new Set(["merchant", "analyst", "admin"].map(role => dashboardHomeForRole(role as "merchant" | "analyst" | "admin"))).size, 3);
});

test("landing memakai endpoint agregat publik dan aset logo resmi", async () => {
  const landing = await readFile("src/app/page.tsx", "utf8");
  const layout = await readFile("src/app/layout.tsx", "utf8");
  const logo = await readFile("src/components/layout/app-logo.tsx", "utf8");
  const metrics = await readFile("src/components/product/public-trust-metrics.tsx", "utf8");
  assert.ok(landing.includes("<PublicTrustMetrics />"));
  assert.ok(metrics.includes('"/public/trust-summary"'));
  assert.doesNotMatch(metrics, /registered_users:\s*\d/);
  assert.ok(logo.includes('"/fingraph-logo.png"'));
  assert.equal((landing.match(/href="#cara-kerja"/g) ?? []).length >= 2, true);
  assert.ok(landing.includes("Untuk usaha"));
  assert.ok(landing.includes("Lebih mudah melihat transaksi yang perlu diperiksa"));
  assert.ok(landing.includes("Gunakan sendiri, atau minta tim membantu"));
  assert.ok(landing.includes('"Riwayat pemeriksaan"'));
  assert.ok(layout.includes('icon: "/fingraph-logo.png"'));
  assert.doesNotMatch(landing, /Bukti pembayaran bisa dipalsukan|sebelum pesanan diserahkan/);
  assert.doesNotMatch(landing, /Masuk ke dasbor/);
  assert.ok(landing.includes("landing-fixed-theme"));
  assert.ok(landing.includes("Risiko {score}/100 · Keyakinan {confidence}%"));
});

test("login demo memisahkan tiga peran dan menampilkan kredensial", async () => {
  const login = await readFile("src/app/login/page.tsx", "utf8");
  for (const value of ["Merchant", "Analyst", "Admin", "merchant@fingraph.id", "analyst@fingraph.id", "admin@fingraph.id", "password123"]) {
    assert.ok(login.includes(value));
  }
});

test("detail pembayaran menampilkan skor, confidence, mode, dan alasan", async () => {
  const detail = await readFile("src/app/dashboard/payments/[id]/page.tsx", "utf8");
  const component = await readFile("src/components/product/ui.tsx", "utf8");
  assert.ok(detail.includes("<AIAnalysisCard"));
  assert.ok(component.includes("Skor risiko"));
  assert.ok(component.includes("Keyakinan hasil"));
  assert.ok(component.includes("Alasan utama:"));
  assert.ok(component.includes("Pemeriksaan pola tidak dipakai untuk pembayaran ini."));
});
