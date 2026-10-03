import {
  DataState,
  PageHeader as ProductPageHeader,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import type { PresentationTone } from "@/lib/presentation";

export { DataState };
export function PageHeader({
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <ProductPageHeader
      title={title}
      description={description}
      action={action}
    />
  );
}
export function RiskBadge({ level }: { level: string }) {
  return <StatusBadge value={level} />;
}
export function MetricCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "slate" | "green" | "amber" | "red" | "cyan" | "neutral";
}) {
  const mapped: PresentationTone =
    tone === "green"
      ? "success"
      : tone === "amber"
        ? "warning"
        : tone === "red"
          ? "danger"
          : tone === "cyan"
            ? "info"
            : "neutral";
  return <SummaryStrip items={[{ label, value, hint, tone: mapped }]} />;
}
