"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import { useTheme } from "next-themes";
import Link from "next/link";
import {
  DatabaseZap,
  Focus,
  RefreshCw,
  ShieldAlert,
  Tags,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { toast } from "sonner";

import {
  DataState,
  DetailList,
  FilterBar,
  PageHeader,
  SearchInput,
  SummaryStrip,
} from "@/components/product/ui";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";

cytoscape.use(coseBilkent);

type GraphNode = {
  id: string;
  label: string;
  title?: string;
  risk_level?: string;
  fraud_score?: number;
  amount?: number;
  status?: string;
  [key: string]: unknown;
};
type GraphEdge = { id: string; source: string; target: string; label: string; event_count?: number; first_seen?: string; last_seen?: string; evidence_payment_id?: string; evidence_reference?: string; source_type?: string };
type GraphResponse = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  returned_nodes?: number;
  total_nodes?: number;
  returned_edges?: number;
  total_edges?: number;
  truncated?: boolean;
  source?: string;
  privacy?: string;
};
const MAX_RENDERED_NODES = 80;

export default function GraphPage() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const { resolvedTheme } = useTheme();
  const [graph, setGraph] = useState<GraphResponse>({ nodes: [], edges: [] });
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [risk, setRisk] = useState("all");
  const [entity, setEntity] = useState("all");
  const [search, setSearch] = useState(() => typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("search") ?? "");
  const [labelsVisible, setLabelsVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const visibleGraph = useMemo<GraphResponse>(() => {
    if (graph.nodes.length <= MAX_RENDERED_NODES) return graph;
    const priority = (node: GraphNode) =>
      node.risk_level === "high" ? 3 : node.risk_level === "medium" ? 2 : 1;
    const nodes = [...graph.nodes]
      .sort((a, b) => priority(b) - priority(a))
      .slice(0, MAX_RENDERED_NODES);
    const visibleIds = new Set(nodes.map((node) => node.id));
    return {
      ...graph,
      nodes,
      edges: graph.edges.filter(
        (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
      ),
    };
  }, [graph]);

  const query = useMemo(() => {
    const params = new URLSearchParams({ limit: "60" });
    if (risk !== "all") params.set("risk_level", risk);
    if (entity !== "all") params.set("entity_type", entity);
    if (search.trim()) params.set("search", search.trim());
    return `/graph?${params}`;
  }, [risk, entity, search]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setGraph(await apiFetch<GraphResponse>(query));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Graph belum dapat dimuat",
      );
    } finally {
      setLoading(false);
    }
  }, [query]);

  async function sync() {
    setSyncing(true);
    try {
      const result = await apiFetch<{ message: string }>("/graph/sync", {
        method: "POST",
      });
      toast.success(result.message);
      await load();
    } catch (reason) {
      toast.error(
        reason instanceof Error ? reason.message : "Sinkronisasi gagal",
      );
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!containerRef.current || !visibleGraph.nodes.length) return;
    const elements: ElementDefinition[] = [
      ...visibleGraph.nodes.map((node) => ({
        data: { ...node, id: node.id, shortTitle: shortNodeTitle(node) },
        classes: `${node.label.toLowerCase()} ${node.risk_level ?? "low"}${labelsVisible ? " labels" : ""}`,
      })),
      ...visibleGraph.edges.map((edge) => ({ data: edge })),
    ];
    const colors = graphColors();
    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.3,
      maxZoom: 3,
      style: graphStyles(colors),
      layout: {
        name: "cose-bilkent",
        animate: false,
        fit: true,
        padding: 56,
        nodeRepulsion: 7600,
        idealEdgeLength: 92,
      } as cytoscape.LayoutOptions,
    });
    cy.on("tap", "node", (event) => {
      event.target.select();
      setSelected(event.target.data() as GraphNode);
      setSelectedEdge(null);
    });
    cy.on("tap", "edge", (event) => {
      event.target.select();
      setSelectedEdge(event.target.data() as GraphEdge);
      setSelected(null);
    });
    cy.on("tap", (event) => {
      if (event.target === cy) {
        cy.elements().unselect();
        setSelected(null);
        setSelectedEdge(null);
      }
    });
    cy.on("mouseover", "node", (event) => event.target.addClass("hovered"));
    cy.on("mouseout", "node", (event) => event.target.removeClass("hovered"));
    cy.on("zoom", () => cy.nodes().toggleClass("zoomed", cy.zoom() >= 1.35));
    if (search.trim() && visibleGraph.nodes[0]) {
      const match = cy.getElementById(visibleGraph.nodes[0].id);
      match.select();
      cy.animate({
        center: { eles: match },
        zoom: Math.max(cy.zoom(), 1.2),
        duration: 250,
      });
    }
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [visibleGraph, labelsVisible, resolvedTheme, search]);

  const high = graph.nodes.filter((node) => node.risk_level === "high").length;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Hubungan pembayaran"
        description="Lihat hubungan antar-pembayaran untuk membantu menemukan pola. Hubungan ini bukan bukti penipuan."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={load}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Muat ulang
            </Button>
            <Button onClick={sync} disabled={syncing}>
              <DatabaseZap className="mr-2 h-4 w-4" />
              {syncing ? "Menyinkronkan…" : "Sinkron graph"}
            </Button>
          </div>
        }
      />
      <SummaryStrip
        items={[
          {
            label: "Node tampil",
            value: `${visibleGraph.nodes.length} / ${graph.total_nodes ?? graph.nodes.length}`,
          },
          {
            label: "Relasi tampil",
            value: `${visibleGraph.edges.length} / ${graph.total_edges ?? graph.edges.length}`,
          },
          { label: "Risiko tinggi", value: high, tone: "danger" },
          {
            label: "Sumber aktif",
            value:
              graph.source === "postgresql_fallback" ? "Fallback DB" : "Neo4j",
            tone: "info",
          },
        ]}
      />
      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          className="flex-1"
          placeholder="Cari referensi, usaha, atau pembayar…"
        />
        <Select value={risk} onValueChange={setRisk}>
          <SelectTrigger className="h-11 w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua risiko</SelectItem>
            <SelectItem value="low">Risiko rendah</SelectItem>
            <SelectItem value="medium">Perlu diperiksa</SelectItem>
            <SelectItem value="high">Berisiko saja</SelectItem>
          </SelectContent>
        </Select>
        <Select value={entity} onValueChange={setEntity}>
          <SelectTrigger className="h-11 w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua entitas</SelectItem>
            {[
              "Payer",
              "Payment",
              "Merchant",
              "Outlet",
              "QRISProfile",
              "PJP",
              "Region",
              "Country",
              "Order",
              "Alert",
            ].map((value) => (
              <SelectItem key={value} value={value}>
                {value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterBar>
      <DataState
        loading={loading}
        error={error}
        empty={!graph.nodes.length}
        onRetry={load}
        emptyTitle="Belum ada hubungan transaksi"
        emptyDescription="Hubungan pembayaran akan muncul setelah ada pembayaran."
      >
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
          <section className="overflow-hidden rounded-xl border border-border bg-surface">
            <div className="flex flex-col gap-3 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-sm font-medium">Kanvas hubungan</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Klik node atau relasi untuk melihat sumber dan bukti
                </p>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10"
                  title="Perbesar"
                  aria-label="Perbesar graph"
                  onClick={() =>
                    cyRef.current?.zoom({
                      level: Math.min((cyRef.current?.zoom() ?? 1) * 1.2, 3),
                      renderedPosition: {
                        x: (containerRef.current?.clientWidth ?? 0) / 2,
                        y: (containerRef.current?.clientHeight ?? 0) / 2,
                      },
                    })
                  }
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10"
                  title="Perkecil"
                  aria-label="Perkecil graph"
                  onClick={() =>
                    cyRef.current?.zoom({
                      level: Math.max((cyRef.current?.zoom() ?? 1) / 1.2, 0.3),
                      renderedPosition: {
                        x: (containerRef.current?.clientWidth ?? 0) / 2,
                        y: (containerRef.current?.clientHeight ?? 0) / 2,
                      },
                    })
                  }
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10"
                  title="Paskan ke layar"
                  aria-label="Paskan graph ke layar"
                  onClick={() => cyRef.current?.fit(undefined, 50)}
                >
                  <Focus className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-10 w-10",
                    labelsVisible && "bg-accent text-accent-foreground",
                  )}
                  title="Tampilkan semua label"
                  aria-label="Tampilkan semua label"
                  aria-pressed={labelsVisible}
                  onClick={() => setLabelsVisible((value) => !value)}
                >
                  <Tags className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-10 w-10",
                    risk === "high" && "bg-danger-soft text-danger",
                  )}
                  title="Tampilkan risiko tinggi"
                  aria-label="Tampilkan node risiko tinggi"
                  aria-pressed={risk === "high"}
                  onClick={() =>
                    setRisk((value) => (value === "high" ? "all" : "high"))
                  }
                >
                  <ShieldAlert className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div
              ref={containerRef}
              className="h-[520px] w-full bg-surface-subtle sm:h-[600px]"
            />
          </section>
          <aside className="space-y-5">
            <section className="rounded-xl border border-border bg-surface p-5">
              <h2 className="font-medium">Detail pilihan</h2>
              {selected ? (
                <div className="mt-3">
                  <DetailList
                    items={[
                      { label: "Tipe", value: selected.label },
                      {
                        label: "Nama",
                        value: String(selected.title ?? selected.id),
                      },
                      {
                        label: "Risiko",
                        value: String(selected.risk_level ?? "—"),
                      },
                      ...(selected.status
                        ? [{ label: "Status", value: String(selected.status) }]
                        : []),
                      { label: "ID", value: selected.id, mono: true },
                    ]}
                  />
                </div>
              ) : selectedEdge ? (
                <div className="mt-3">
                  <DetailList items={[
                    { label: "Relasi", value: relationLabel(selectedEdge.label) },
                    { label: "Jumlah pembayaran", value: selectedEdge.event_count ?? 1 },
                    { label: "Pertama terlihat", value: selectedEdge.first_seen ? formatDateTime(selectedEdge.first_seen) : "—" },
                    { label: "Terakhir terlihat", value: selectedEdge.last_seen ? formatDateTime(selectedEdge.last_seen) : "—" },
                    { label: "Sumber", value: selectedEdge.source_type === "payment_events" ? "Data pembayaran" : selectedEdge.source_type ?? "—" },
                  ]} />
                  {selectedEdge.evidence_payment_id && <Link href={`/dashboard/payments/${selectedEdge.evidence_payment_id}`} className="mt-4 inline-flex text-sm font-medium text-primary">Buka bukti {selectedEdge.evidence_reference ?? "pembayaran"}</Link>}
                  <p className="mt-4 text-xs leading-5 text-muted-foreground">Relasi menunjukkan asosiasi pada data yang tersedia, bukan kesimpulan fraud.</p>
                </div>
              ) : (
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Pilih satu node atau relasi untuk melihat informasi yang aman ditampilkan.
                </p>
              )}
            </section>
            <section className="rounded-xl border border-border bg-surface p-5">
              <h2 className="font-medium">Legenda</h2>
              <div className="mt-4 space-y-3">
                {[
                  ["bg-primary", "Payment"],
                  ["bg-info", "Payer"],
                  ["bg-success", "Merchant / Outlet"],
                  ["bg-warning", "Region / Country"],
                  ["bg-danger", "Risiko tinggi"],
                ].map(([color, label]) => (
                  <div
                    key={label}
                    className="flex items-center gap-2.5 text-sm text-muted-foreground"
                  >
                    <span className={cn("h-3 w-3 rounded-full", color)} />
                    {label}
                  </div>
                ))}
              </div>
            </section>
            <p className="text-xs leading-5 text-muted-foreground">
              {graph.privacy ??
                "Identitas payer ditampilkan dalam bentuk pseudonym."}
            </p>
          </aside>
        </div>
      </DataState>
    </div>
  );
}

function relationLabel(value: string) {
  return ({
    PAYER_MADE_PAYMENT: "Pembayar melakukan pembayaran",
    PAYMENT_TO_MERCHANT: "Pembayaran masuk ke usaha",
    MERCHANT_HAS_OUTLET: "Merchant memiliki outlet",
    OUTLET_USES_QRIS: "Outlet menggunakan profil QRIS",
    PAYMENT_VIA_PJP: "Pembayaran diterima melalui penyedia",
    PAYMENT_FROM_REGION: "Pembayaran berasal dari wilayah",
    PAYMENT_FROM_COUNTRY: "Pembayaran berasal dari negara",
    PAYMENT_FOR_ORDER: "Pembayaran terkait pesanan",
    LINKED_TO_ALERT: "Pembayaran menghasilkan peringatan",
  } as Record<string, string>)[value] ?? value.replaceAll("_", " ");
}

function shortNodeTitle(node: GraphNode) {
  const value = String(node.title ?? node.id);
  if (node.label.toLowerCase() === "payer")
    return `${value.slice(0, 8)}…${value.slice(-4)}`;
  return value.length > 22 ? `${value.slice(0, 19)}…` : value;
}

function graphColors() {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback;
  return {
    primary: read("--primary", "#000000"),
    info: read("--info", "#4D6266"),
    success: read("--success", "#137A3E"),
    warning: read("--warning", "#8A5600"),
    danger: read("--danger", "#B42318"),
    surface: read("--surface-raised", "#FFFFFF"),
    foreground: read("--foreground", "#000000"),
    border: read("--border", "#E4E4E7"),
    muted: read("--muted-foreground", "#52525B"),
  };
}

function graphStyles(
  colors: ReturnType<typeof graphColors>,
): cytoscape.StylesheetStyle[] {
  const labelStyle = {
    label: "data(shortTitle)",
    color: colors.foreground,
    "font-size": 10,
    "font-family": "IBM Plex Mono, monospace",
    "text-background-color": colors.surface,
    "text-background-opacity": 0.94,
    "text-background-padding": "3px",
    "text-valign": "bottom",
    "text-margin-y": 8,
  } as const;
  return [
    {
      selector: "node",
      style: {
        "background-color": colors.primary,
        label: "",
        width: 32,
        height: 32,
        "border-width": 2,
        "border-color": colors.surface,
      },
    },
    {
      selector: "node.hovered, node:selected, node.zoomed, node.labels",
      style: labelStyle,
    },
    {
      selector: "node.payer",
      style: { "background-color": colors.info, shape: "round-rectangle" },
    },
    {
      selector: "node.merchant, node.outlet",
      style: { "background-color": colors.success, shape: "rectangle" },
    },
    {
      selector: "node.region, node.country",
      style: { "background-color": colors.warning },
    },
    {
      selector: "node.alert, node.high",
      style: {
        "background-color": colors.danger,
        "border-color": colors.danger,
        "border-width": 3,
      },
    },
    {
      selector: "node.medium",
      style: { "border-color": colors.warning, "border-width": 3 },
    },
    {
      selector: "edge",
      style: {
        width: 1.1,
        "line-color": colors.border,
        "target-arrow-color": colors.muted,
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        opacity: 0.68,
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-color": colors.foreground,
        "border-width": 4,
        width: 38,
        height: 38,
      },
    },
    {
      selector: "edge:selected",
      style: { width: 3, "line-color": colors.foreground, "target-arrow-color": colors.foreground, opacity: 1 },
    },
  ];
}
