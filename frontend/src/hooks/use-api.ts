"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true); setError(null);
    try { setData(await apiFetch<T>(path)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Data gagal dimuat"); }
    finally { setLoading(false); }
  }, [path]);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => { if (!controller.signal.aborted) void reload(); });
    return () => controller.abort();
  }, [reload]);
  return { data, loading, error, reload, setData };
}
