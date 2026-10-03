import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function AppLogo({ href = "/", compact = false, inverted = false, className }: { href?: string; compact?: boolean; inverted?: boolean; className?: string }) {
  return (
    <Link href={href} aria-label="FinGraph QRIS" className={cn("group inline-flex items-center gap-2.5", className)}>
      <span className={cn("relative h-10 w-10 shrink-0 overflow-hidden rounded-lg", inverted && "ring-1 ring-white/15")}>
        <Image
          src="/fingraph-logo.png"
          alt="FinGraph logo"
          fill
          sizes="40px"
          priority
          className="scale-[1.8] object-contain"
        />
      </span>
      {!compact && <span className="leading-none"><span className="block text-[17px] font-semibold tracking-[-.025em]">FinGraph</span><span className={cn("mt-1 block text-[10px] font-medium tracking-[.17em]", inverted ? "text-zinc-400" : "text-muted-foreground")}>QRIS</span></span>}
    </Link>
  );
}
