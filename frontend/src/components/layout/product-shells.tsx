"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BrainCircuit,
  Building2,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  CreditCard,
  FlaskConical,
  Globe2,
  History,
  Home,
  LogOut,
  MoreHorizontal,
  Network,
  QrCode,
  ReceiptText,
  Settings,
  ShoppingBag,
  Store,
  SunMoon,
  UserRound,
} from "lucide-react";
import { AppLogo } from "@/components/layout/app-logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  OutletProvider,
  useSelectedOutlet,
} from "@/components/providers/outlet-provider";
import { logout, type User } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { isDemoBuild } from "@/lib/runtime";
import { PlanBadge } from "@/components/product/pricing";
import { useSubscription } from "@/components/providers/subscription-provider";
import { planAtLeast } from "@/lib/plans";

type NavItem = {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
};
const merchantNav: NavItem[] = [
  { label: "Beranda", href: "/dashboard", icon: Home, exact: true },
  { label: "Pembayaran", href: "/dashboard/payments", icon: ReceiptText },
  { label: "Pesanan", href: "/dashboard/orders", icon: ShoppingBag },
  { label: "Peringatan", href: "/dashboard/alerts", icon: AlertTriangle },
  { label: "Laporan", href: "/dashboard/reports", icon: BarChart3 },
];
const analystGroups: { label: string; items: NavItem[] }[] = [
  { label: "REVIEW", items: [
    { label: "Ringkasan", href: "/dashboard", icon: Home, exact: true },
    { label: "Investigasi", href: "/dashboard/payments", icon: ClipboardList },
  ] },
  { label: "KONTEKS", items: [
    { label: "Merchant", href: "/dashboard/merchants", icon: Store },
    { label: "Graph", href: "/dashboard/graph", icon: Network },
    { label: "Lintas Wilayah", href: "/dashboard/cross-border", icon: Globe2 },
  ] },
  { label: "TEKNIS", items: [
    { label: "Model", href: "/dashboard/ml", icon: BrainCircuit },
    { label: "Prototype FL", href: "/dashboard/federated", icon: Building2 },
    { label: "Audit", href: "/dashboard/audit-logs", icon: History },
  ] },
];
const analystPrimary = analystGroups.flatMap((group) => group.items);

function activePath(pathname: string, item: NavItem) {
  return item.exact ? pathname === item.href : pathname.startsWith(item.href);
}

export function DashboardShell({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  return user.role === "merchant" ? (
    <AppShellMerchant user={user}>{children}</AppShellMerchant>
  ) : (
    <AppShellAnalyst user={user}>{children}</AppShellAnalyst>
  );
}

export function AppShellMerchant({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  return (
    <OutletProvider>
      <div className="min-h-screen bg-background">
        <MerchantSidebar user={user} />
        <div className="min-h-screen lg:pl-[232px]">
          <TopBar user={user} merchant />
          <main className="mx-auto w-full max-w-[1320px] px-4 pb-[calc(10rem+env(safe-area-inset-bottom))] pt-5 sm:px-6 sm:pt-7 lg:px-8 lg:pb-10">
            {children}
          </main>
        </div>
        <MobileBottomNav />
      </div>
    </OutletProvider>
  );
}

export function MerchantSidebar({ user }: { user: User }) {
  const pathname = usePathname();
  const { plan } = useSubscription();
  const visibleNavigation = merchantNav.filter(
    (item) => item.href !== "/dashboard/reports" || planAtLeast(plan, "growth"),
  );
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[232px] border-r border-border bg-surface lg:block">
      <div className="flex h-full flex-col">
        <div className="flex h-[68px] items-center px-5">
          <AppLogo href="/dashboard" />
        </div>
        <div className="px-4 pt-2">
          <Button
            asChild
            className="h-11 w-full justify-start rounded-xl shadow-sm"
          >
            <Link href="/dashboard/payments/check">
              <QrCode className="mr-2.5 h-[18px] w-[18px]" />
              Cek Pembayaran
            </Link>
          </Button>
        </div>
        <nav
          aria-label="Navigasi merchant"
          className="mt-5 flex-1 space-y-1 px-3"
        >
          {visibleNavigation.map((item) => (
            <SidebarLink
              key={item.href}
              item={item}
              active={activePath(pathname, item)}
            />
          ))}
        </nav>
        <div className="border-t border-border p-3">
          <UserMenu
            user={user}
            align="start"
            triggerClassName="w-full justify-start"
          />
        </div>
      </div>
    </aside>
  );
}

export function MobileBottomNav() {
  const pathname = usePathname();
  const { plan } = useSubscription();
  const items = [
    merchantNav[0],
    merchantNav[1],
    { label: "Cek", href: "/dashboard/payments/check", icon: QrCode },
    merchantNav[3],
  ];
  const moreActive = [
    "/dashboard/orders",
    "/dashboard/reports",
    "/dashboard/qris",
    "/dashboard/help",
    "/dashboard/settings",
  ].some((path) => pathname.startsWith(path));
  return (
    <nav
      aria-label="Navigasi mobile"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface px-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-1.5 shadow-[0_-8px_24px_color-mix(in_srgb,var(--foreground)_7%,transparent)] lg:hidden"
    >
      <div className="mx-auto grid max-w-md grid-cols-5">
        {items.map((item, index) => {
          const active = activePath(pathname, item);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-medium text-muted-foreground",
                active && "text-primary",
              )}
              aria-current={active ? "page" : undefined}
            >
              {index === 2 ? (
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                  <Icon className="h-5 w-5" />
                </span>
              ) : (
                <Icon className="h-5 w-5" />
              )}
              <span>{item.label}</span>
            </Link>
          );
        })}
        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(
              "flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-medium text-muted-foreground",
              moreActive && "text-primary",
            )}
            aria-label="Buka menu lainnya"
          >
            <MoreHorizontal className="h-5 w-5" />
            <span>Lainnya</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="mb-2 w-56">
            <DropdownMenuItem asChild>
              <Link href="/dashboard/orders">
                <ShoppingBag />
                Pesanan
              </Link>
            </DropdownMenuItem>
            {planAtLeast(plan, "growth") && (
              <DropdownMenuItem asChild>
                <Link href="/dashboard/reports">
                  <BarChart3 />
                  Laporan
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem asChild>
              <Link href="/dashboard/plans">
                <CreditCard />
                Paket FinGraph
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/qris">
                <QrCode />
                QRIS dan Outlet
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/help">
                <CircleHelp />
                Pusat Bantuan
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings">
                <Settings />
                Pengaturan
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  );
}

export function AppShellAnalyst({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const secondary: NavItem[] =
    user.role === "admin"
      ? [
          {
            label: "Monitoring Aktivitas",
            href: "/dashboard/admin-monitoring",
            icon: Activity,
          },
          {
            label: "Konfigurasi Risiko",
            href: "/dashboard/risk-config",
            icon: Settings,
          },
          ...(isDemoBuild
            ? [
                {
                  label: "Demo Lab",
                  href: "/dashboard/simulation",
                  icon: FlaskConical,
                },
              ]
            : []),
        ]
      : [];
  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] border-r border-border bg-surface lg:block">
        <div className="flex h-full flex-col">
          <div className="flex h-[68px] items-center border-b border-border px-5">
            <AppLogo href="/dashboard" />
          </div>
          <nav className="no-scrollbar flex-1 overflow-y-auto px-3 py-4">
            {analystGroups.map((group, index) => (
              <div key={group.label}>
                <p className={`${index ? "mt-5 " : ""}px-3 pb-2 text-[11px] font-bold tracking-[.12em] text-muted-foreground`}>{group.label}</p>
                {group.items.map((item) => <AnalystLink key={item.href} item={item} active={activePath(pathname, item)} />)}
              </div>
            ))}
            {secondary.length > 0 && (
              <>
                <p className="mt-5 px-3 pb-2 text-[11px] font-bold tracking-[.12em] text-muted-foreground">
                  ADMIN
                </p>
                {secondary.map((item) => (
                  <AnalystLink
                    key={item.href}
                    item={item}
                    active={activePath(pathname, item)}
                  />
                ))}
              </>
            )}
          </nav>
          <div className="border-t border-border p-3">
            <UserMenu
              user={user}
              align="start"
              triggerClassName="w-full justify-start"
            />
          </div>
        </div>
      </aside>
      <div className="min-h-screen lg:pl-[248px]">
        <TopBar user={user} />
        <AnalystMobileNav items={[...analystPrimary, ...secondary]} />
        <main className="mx-auto w-full max-w-[1440px] px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function AnalystMobileNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Navigasi analyst mobile"
      className="no-scrollbar sticky top-16 z-10 overflow-x-auto overflow-y-hidden border-b border-border bg-surface px-3 py-2 lg:hidden"
    >
      <div className="flex min-w-max gap-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = activePath(pathname, item);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-10 items-center gap-2 whitespace-nowrap rounded-lg px-3 text-xs font-medium text-muted-foreground",
                active && "bg-accent text-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-subtle hover:text-foreground",
        active && "bg-accent text-accent-foreground",
      )}
    >
      <Icon className="h-[18px] w-[18px]" />
      {item.label}
    </Link>
  );
}
function AnalystLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "mb-0.5 flex min-h-10 items-center gap-3 rounded-lg px-3 text-[13px] font-medium text-muted-foreground transition hover:bg-surface-subtle hover:text-foreground",
        active && "bg-accent text-accent-foreground",
      )}
    >
      <Icon className="h-4 w-4" />
      {item.label}
    </Link>
  );
}

export function TopBar({
  user,
  merchant = false,
}: {
  user: User;
  merchant?: boolean;
}) {
  const { plan } = useSubscription();
  return (
    <header className="sticky top-0 z-20 flex h-[64px] items-center justify-between border-b border-border bg-surface px-4 sm:px-6 lg:px-8">
      <div className="lg:hidden">
        <AppLogo href="/dashboard" />
      </div>
      <div className="hidden items-center gap-3 lg:flex">
        {merchant ? (
          <OutletSwitcher />
        ) : (
          <>
            <span className="rounded-md border border-border bg-surface-subtle px-2 py-1 text-[11px] font-bold text-muted-foreground">
              {user.role === "admin" ? "MODE ADMIN" : "MODE ANALYST"}
            </span>
            <span className="text-sm text-muted-foreground">
              {user.role === "admin"
                ? "Kendali dan monitoring"
                : "Ruang investigasi"}
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-1">
        <Link
          href={user.role === "merchant" ? "/dashboard/plans" : "/dashboard"}
          className="mr-1 hidden sm:block"
          aria-label={`Paket ${plan}`}
        >
          <PlanBadge plan={plan} compact />
        </Link>
        {isDemoBuild && (
          <span className="mr-1 hidden rounded-md bg-info-soft px-2 py-1 text-[10px] font-bold text-info sm:inline">
            DEMO
          </span>
        )}
        <Button
          asChild
          variant="ghost"
          size="icon"
          className="h-11 w-11"
          title="Notifikasi"
        >
          <Link href="/dashboard/alerts" aria-label="Lihat notifikasi">
            <Bell className="h-[18px] w-[18px]" />
          </Link>
        </Button>
        <ThemeToggle />
        <UserMenu user={user} />
      </div>
    </header>
  );
}

export function OutletSwitcher() {
  const { outlets, selectedId, setSelectedId, loading } = useSelectedOutlet();
  if (loading)
    return (
      <span className="text-sm text-muted-foreground">Memuat outlet…</span>
    );
  return (
    <Select value={selectedId} onValueChange={setSelectedId}>
      <SelectTrigger
        aria-label="Pilih outlet"
        className="h-9 min-w-44 border-0 bg-secondary shadow-none"
      >
        <Store className="mr-2 h-4 w-4 text-primary" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Semua outlet</SelectItem>
        {outlets.map((item) => (
          <SelectItem key={item.id} value={item.id}>
            {item.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function UserMenu({
  user,
  align = "end",
  triggerClassName,
}: {
  user: User;
  align?: "start" | "end";
  triggerClassName?: string;
}) {
  const { plan } = useSubscription();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className={cn("h-11 gap-2 px-2.5", triggerClassName)}
        >
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-surface-subtle text-primary">
            <UserRound className="h-4 w-4" />
          </span>
          <span className="hidden max-w-32 truncate text-left text-sm font-medium sm:block">
            {user.full_name}
          </span>
          <ChevronDown className="hidden h-3.5 w-3.5 opacity-60 sm:block" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className="w-60">
        <DropdownMenuLabel>
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm">{user.full_name}</p>
            <PlanBadge plan={plan} compact />
          </div>
          <p className="mt-0.5 truncate text-xs font-normal text-muted-foreground">
            {user.email}
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {user.role === "merchant" && (
          <>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/plans">
                <CreditCard />
                Paket dan fitur
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings">
                <Store />
                Profil Usaha
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/qris">
                <QrCode />
                QRIS dan Outlet
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings?tab=appearance">
                <SunMoon />
                Pengaturan Tampilan
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/help">
                <CircleHelp />
                Pusat Bantuan
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem onClick={logout} variant="destructive">
          <LogOut />
          Keluar
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
