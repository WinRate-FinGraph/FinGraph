import { expect, Page, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const outputDirectory = path.resolve(process.cwd(), ".visual-qa");
mkdirSync(outputDirectory, { recursive: true });

async function setTheme(page: Page, theme: "light" | "dark" | null) {
  if (theme !== null) await page.addInitScript(value => {
    if (localStorage.getItem("fingraph-theme") === null) localStorage.setItem("fingraph-theme", value);
  }, theme);
}

async function login(page: Page, role: "merchant" | "analyst" | "admin") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${role}@fingraph.id`);
  await page.getByLabel("Kata sandi").fill("password123");
  await page.getByRole("button", { name: "Masuk", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
  await expect(page.getByRole("heading").first()).toBeVisible();
}

async function settle(page: Page) {
  await page.waitForLoadState("domcontentloaded");
  await expect(page.locator('[aria-label="Menyiapkan ruang kerja"]')).toBeHidden({ timeout: 12_000 });
  await page.waitForTimeout(700);
}

async function assertNoDocumentOverflow(page: Page) {
  const result = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
  expect(result.scrollWidth, `document overflow: ${JSON.stringify(result)}`).toBeLessThanOrEqual(result.width + 1);
}

async function assertTabsDoNotOverflowVertically(page: Page) {
  const values = await page.locator('[data-slot="tabs-list"]').evaluateAll(elements => elements.map(element => ({ client: element.clientHeight, scroll: element.scrollHeight })));
  for (const value of values) expect(value.scroll).toBeLessThanOrEqual(value.client + 1);
}

async function shot(page: Page, name: string, options: { allowDemoSlugs?: boolean } = {}) {
  await settle(page);
  const reveals = page.locator(".landing-reveal");
  for (let index = 0; index < await reveals.count(); index += 1) {
    await reveals.nth(index).scrollIntoViewIfNeeded();
    await expect(reveals.nth(index)).toHaveClass(/is-visible/);
  }
  await page.evaluate(() => {
    document.documentElement.style.setProperty("scroll-behavior", "auto", "important");
    document.body.style.setProperty("scroll-behavior", "auto", "important");
    window.scrollTo(0, 0);
  });
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await page.waitForTimeout(250);
  await assertNoDocumentOverflow(page);
  await assertTabsDoNotOverflowVertically(page);
  if (!options.allowDemoSlugs) {
    await expect(page.locator("body")).not.toHaveText(/normal_payment|duplicate_reference|suspicious_network|merchant_qris_mismatch/);
  }
  const publicHeader = page.locator("main > header").first();
  if (await publicHeader.count()) {
    await publicHeader.evaluate((element) => {
      (element as HTMLElement).style.position = "static";
    });
  }
  await page.screenshot({ path: path.join(outputDirectory, `${name}.png`), fullPage: true });
}

test("theme defaults, persistence, and landing structure", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/light/);
  const hero = page.getByTestId("hero-visual");
  await expect(hero).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pastikan pembayaran masuk sebelum pesanan diserahkan." })).toBeVisible();
  await expect(page.getByText("Akun demo", { exact: true })).toBeVisible();
  const boxes = await page.evaluate(() => {
    const visual = document.querySelector('[data-testid="hero-visual"]')!.getBoundingClientRect();
    const section = document.querySelector('[data-testid="hero-visual"]')!.closest("section")!.getBoundingClientRect();
    const header = document.querySelector("header")!.getBoundingClientRect();
    return { visual: { top: visual.top, bottom: visual.bottom, left: visual.left, right: visual.right }, section: { top: section.top, bottom: section.bottom, left: section.left, right: section.right }, headerBottom: header.bottom };
  });
  expect(boxes.visual.left).toBeGreaterThanOrEqual(boxes.section.left);
  expect(boxes.visual.right).toBeLessThanOrEqual(boxes.section.right + 1);
  expect(boxes.visual.bottom).toBeLessThanOrEqual(boxes.section.bottom + 1);
  expect(boxes.visual.top).toBeGreaterThanOrEqual(boxes.headerBottom);

  await page.evaluate(() => localStorage.setItem("fingraph-theme", "dark"));
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.evaluate(() => localStorage.setItem("fingraph-theme", "light"));
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/light/);
});

test("light desktop screenshot matrix", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setTheme(page, "light");
  await page.goto("/");
  await shot(page, "light-desktop-1440x900-landing");
  await login(page, "merchant");
  await expect(page.locator("aside").first()).toBeVisible();
  await page.getByRole("button", { name: "Gunakan tema gelap" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.getByRole("button", { name: "Gunakan tema terang" }).click();
  await expect(page.locator("html")).toHaveClass(/light/);
  for (const [route, name] of [["/dashboard", "merchant-home"], ["/dashboard/payments", "payments"], ["/dashboard/orders", "orders"], ["/dashboard/alerts", "alerts"], ["/dashboard/reports", "reports"]] as const) { await page.goto(route); await shot(page, `light-desktop-1440x900-${name}`); }
  await page.evaluate(() => { localStorage.removeItem("fingraph_token"); localStorage.removeItem("fingraph_user"); });
  await login(page, "analyst");
  for (const [route, name] of [["/dashboard", "analyst-home"], ["/dashboard/graph", "graph"], ["/dashboard/federated", "federated"]] as const) { await page.goto(route); await shot(page, `light-desktop-1440x900-${name}`); }
});

test("dark desktop screenshot matrix", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setTheme(page, "dark");
  await page.goto("/");
  await shot(page, "dark-desktop-1440x900-landing");
  await login(page, "merchant");
  for (const [route, name] of [["/dashboard", "merchant-home"], ["/dashboard/payments", "payments"]] as const) { await page.goto(route); await shot(page, `dark-desktop-1440x900-${name}`); }
  await page.evaluate(() => { localStorage.removeItem("fingraph_token"); localStorage.removeItem("fingraph_user"); });
  await login(page, "analyst");
  await page.goto("/dashboard");
  await shot(page, "dark-desktop-1440x900-analyst-home");
});

test("light mobile screenshot matrix", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setTheme(page, "light");
  await page.goto("/");
  await shot(page, "light-mobile-390x844-landing");
  await login(page, "merchant");
  await expect(page.getByRole("navigation", { name: "Navigasi mobile" })).toBeVisible();
  for (const [route, name] of [["/dashboard", "merchant-home"], ["/dashboard/payments", "payments"], ["/dashboard/payments/check", "payment-check"], ["/dashboard/alerts", "alerts"]] as const) { await page.goto(route); await shot(page, `light-mobile-390x844-${name}`); }
});

test("light tablet screenshot matrix", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await setTheme(page, "light");
  await login(page, "merchant");
  for (const [route, name] of [["/dashboard", "merchant-home"], ["/dashboard/payments", "payments"]] as const) { await page.goto(route); await shot(page, `light-tablet-768x1024-${name}`); }
});

test("supplemental light desktop page coverage", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setTheme(page, "light");

  for (const [route, name] of [["/login", "login"], ["/register", "register"]] as const) {
    await page.goto(route);
    await expect(page.locator("html")).toHaveClass(/light/);
    await shot(page, `light-desktop-1440x900-${name}`);
  }

  await login(page, "merchant");
  await page.goto("/dashboard/payments");
  const detailHref = await page.getByRole("link", { name: /^Tinjau pembayaran/ }).first().getAttribute("href");
  expect(detailHref).toMatch(/^\/dashboard\/payments\//);
  for (const [route, name] of [
    [detailHref!, "payment-detail"],
    ["/dashboard/payments/check", "payment-check"],
    ["/dashboard/qris", "qris-outlet"],
    ["/dashboard/settings", "settings"],
    ["/dashboard/help", "help"],
  ] as const) {
    await page.goto(route);
    await shot(page, `light-desktop-1440x900-${name}`);
  }

  await page.evaluate(() => { localStorage.removeItem("fingraph_token"); localStorage.removeItem("fingraph_user"); });
  await login(page, "analyst");
  for (const [route, name] of [
    ["/dashboard/payments", "investigations"],
    ["/dashboard/merchants", "merchants"],
    ["/dashboard/cross-border", "cross-border"],
    ["/dashboard/ml", "models"],
    ["/dashboard/audit-logs", "audit"],
  ] as const) {
    await page.goto(route);
    await shot(page, `light-desktop-1440x900-${name}`);
  }

  await page.evaluate(() => { localStorage.removeItem("fingraph_token"); localStorage.removeItem("fingraph_user"); });
  await login(page, "admin");
  await expect(page.getByRole("heading", { name: "Pusat kendali administrator" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Monitoring Aktivitas" })).toBeVisible();
  await page.goto("/dashboard/admin-monitoring");
  await expect(page.getByRole("heading", { name: "Monitoring Aktivitas" })).toBeVisible();
  await expect(page.getByText("Pengguna aktif", { exact: true }).first()).toBeVisible();
  await shot(page, "light-desktop-1440x900-admin-monitoring");
  await page.goto("/dashboard/risk-config");
  await shot(page, "light-desktop-1440x900-risk-config");
  await page.goto("/dashboard/simulation");
  await shot(page, "light-desktop-1440x900-demo-lab", { allowDemoSlugs: true });
});
