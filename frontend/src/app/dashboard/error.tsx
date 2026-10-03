"use client";
import { Button } from "@/components/ui/button";
export default function DashboardError({
  error,
  unstable_retry,
}: {
  error: Error;
  unstable_retry: () => void;
}) {
  return (
    <div className="grid min-h-96 place-items-center text-center">
      <div>
        <h2 className="text-xl font-bold">Halaman mengalami kendala</h2>
        <p className="mt-2 max-w-lg text-sm text-slate-500">{error.message}</p>
        <Button className="mt-5" onClick={unstable_retry}>
          Coba lagi
        </Button>
      </div>
    </div>
  );
}
