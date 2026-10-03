import { normalizePlan, planAtLeast, requiredPlanForPath, type PlanCode } from "./plans.ts";

export type AppRole = "merchant" | "analyst" | "admin";

const analystRoutes = [
  "/dashboard/merchants",
  "/dashboard/graph",
  "/dashboard/cross-border",
  "/dashboard/ml",
  "/dashboard/adaptive",
  "/dashboard/federated",
  "/dashboard/risk-config",
  "/dashboard/simulation",
  "/dashboard/admin-monitoring",
];

const merchantRoutes = [
  "/dashboard/check-payment",
  "/dashboard/orders",
  "/dashboard/qris",
  "/dashboard/reports",
  "/dashboard/plans",
  "/dashboard/help",
  "/dashboard/settings",
];

const adminRoutes = ["/dashboard/risk-config", "/dashboard/simulation", "/dashboard/admin-monitoring"];

export function canAccessDashboardPath(role: AppRole, path: string, subscriptionPlan?: PlanCode) {
  if (role === "merchant") {
    if (analystRoutes.some(prefix => path.startsWith(prefix))) return false;
    return planAtLeast(normalizePlan(subscriptionPlan), requiredPlanForPath(path));
  }
  if (role === "analyst" && adminRoutes.some(prefix => path.startsWith(prefix))) return false;
  return !merchantRoutes.some(prefix => path.startsWith(prefix));
}

export function dashboardHomeForRole(role?: AppRole) {
  if (role === "merchant") return "merchant-home" as const;
  if (role === "admin") return "admin-home" as const;
  return "analyst-home" as const;
}
