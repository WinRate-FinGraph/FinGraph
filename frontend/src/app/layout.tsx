import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "FinGraph QRIS",
  description:
    "Asisten keamanan pembayaran untuk UMKM. Pembayaran jelas, usaha lebih tenang.",
  icons: {
    icon: "/fingraph-logo.png",
    shortcut: "/fingraph-logo.png",
    apple: "/fingraph-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" suppressHydrationWarning data-scroll-behavior="smooth">
      <body className="font-sans antialiased">
        <ThemeProvider>
          {children}
          <Toaster richColors position="top-right" duration={2000} />
        </ThemeProvider>
      </body>
    </html>
  );
}
