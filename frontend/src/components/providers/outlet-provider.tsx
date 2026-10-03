"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";

type Outlet = { id: string; name: string };
type OutletContextValue = {
  outlets: Outlet[];
  selectedId: string;
  selectedName: string | null;
  setSelectedId: (id: string) => void;
  loading: boolean;
};

const OutletContext = createContext<OutletContextValue>({
  outlets: [],
  selectedId: "all",
  selectedName: null,
  setSelectedId: () => undefined,
  loading: true,
});

export function OutletProvider({ children }: { children: React.ReactNode }) {
  const query = useApi<{ items: Outlet[] }>("/merchants/outlets");
  const [selectedId, setSelectedIdState] = useState("all");
  const effectiveId =
    selectedId === "all" ||
    query.data?.items.some((item) => item.id === selectedId)
      ? selectedId
      : "all";
  const value = useMemo<OutletContextValue>(
    () => ({
      outlets: query.data?.items ?? [],
      selectedId: effectiveId,
      selectedName:
        query.data?.items.find((item) => item.id === effectiveId)?.name ?? null,
      setSelectedId: setSelectedIdState,
      loading: query.loading,
    }),
    [effectiveId, query.data, query.loading],
  );
  return (
    <OutletContext.Provider value={value}>{children}</OutletContext.Provider>
  );
}

export function useSelectedOutlet() {
  return useContext(OutletContext);
}
