"use client";
import { useMemo, useState } from "react";
import {
  DataState,
  EmptyState,
  FilterBar,
  PageHeader,
  PaginationBar,
  SearchInput,
  StatusBadge,
  SummaryStrip,
} from "@/components/product/ui";
import { useApi } from "@/hooks/use-api";
import type { PageResponse } from "@/lib/types";

type Merchant = {
  id: string;
  merchant_code: string;
  name: string;
  business_type: string;
  owner_name: string;
  city: string;
  province: string;
  risk_level: string;
  status: string;
};
export default function MerchantsPage() {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (search.trim()) params.set("search", search.trim());
    return `/merchants?${params}`;
  }, [offset, search]);
  const query = useApi<PageResponse<Merchant>>(path);
  return (
    <div className="space-y-6">
      <PageHeader
        title="Merchant"
        description="Direktori UMKM dan tingkat risiko profil yang terdaftar."
      />
      <SummaryStrip
        items={[
          { label: "Merchant terdaftar", value: query.data?.total ?? "—" },
          { label: "Halaman", value: query.data?.page ?? "—" },
          { label: "Total halaman", value: query.data?.total_pages ?? "—" },
        ]}
      />
      <FilterBar>
        <SearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
          className="flex-1"
          placeholder="Cari merchant, kode, atau kota…"
        />
      </FilterBar>
      <DataState
        loading={query.loading}
        error={query.error}
        onRetry={query.reload}
      >
        {query.data &&
          (query.data.items.length ? (
            <>
              <div className="overflow-hidden rounded-xl border bg-card">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-secondary/60 text-xs text-muted-foreground">
                      <tr>
                        <th className="px-5 py-3.5">Merchant</th>
                        <th className="px-4 py-3.5">Jenis usaha</th>
                        <th className="px-4 py-3.5">Lokasi</th>
                        <th className="px-4 py-3.5">Pemilik</th>
                        <th className="px-5 py-3.5">Risiko</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {query.data.items.map((item) => (
                        <tr key={item.id} className="hover:bg-secondary/40">
                          <td className="px-5 py-4">
                            <p className="font-medium">{item.name}</p>
                            <p className="mt-1 font-technical text-xs text-muted-foreground">
                              {item.merchant_code}
                            </p>
                          </td>
                          <td className="px-4 py-4 text-muted-foreground">
                            {item.business_type}
                          </td>
                          <td className="px-4 py-4">
                            {item.city}, {item.province}
                          </td>
                          <td className="px-4 py-4 text-muted-foreground">
                            {item.owner_name}
                          </td>
                          <td className="px-5 py-4">
                            <StatusBadge value={item.risk_level} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <PaginationBar
                total={query.data.total}
                limit={query.data.limit}
                offset={query.data.offset}
                onPageChange={setOffset}
              />
            </>
          ) : (
            <EmptyState
              title="Merchant tidak ditemukan"
              description="Ubah kata kunci pencarian."
            />
          ))}
      </DataState>
    </div>
  );
}
