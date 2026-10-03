"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CircleHelp,
  QrCode,
  ReceiptText,
  Search,
  Store,
} from "lucide-react";

import { PageHeader } from "@/components/product/ui";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const guides = [
  {
    icon: ReceiptText,
    title: "Memeriksa pembayaran",
    body: "Masukkan nomor referensi dan nominal, lalu ikuti tindakan yang ditampilkan.",
    href: "/dashboard/payments/check",
  },
  {
    icon: AlertTriangle,
    title: "Menangani peringatan",
    body: "Tinjau alasan utama sebelum menandai aman, menahan, atau melaporkan pembayaran.",
    href: "/dashboard/alerts",
  },
  {
    icon: QrCode,
    title: "Memastikan QRIS benar",
    body: "Bandingkan profil QRIS dengan data outlet yang tersimpan pada Mode Demo.",
    href: "/dashboard/qris",
  },
];

const faq = [
  [
    "Apakah screenshot cukup sebagai bukti pembayaran?",
    "Tidak. Screenshot dapat diedit. Cari nomor referensi dan tunggu konfirmasi pembayaran sebelum menyerahkan pesanan.",
  ],
  [
    "Apa yang dilakukan saat nominal tidak sesuai?",
    "Tahan pesanan sementara. Minta pelanggan melunasi selisih atau periksa kembali nomor referensi yang diberikan.",
  ],
  [
    "Apa arti Perlu diperiksa?",
    "Pembayaran ditemukan, tetapi ada detail yang perlu dikonfirmasi. Merchant tetap menentukan keputusan akhir.",
  ],
  [
    "Apakah FinGraph terhubung ke bank atau PJP nyata?",
    "Belum. Versi ini menggunakan simulator PJP untuk demonstrasi dan pengujian alur keamanan.",
  ],
  [
    "Apakah FinGraph dapat memblokir dana?",
    "Tidak. FinGraph memberi rekomendasi tindakan kepada merchant dan tidak mengendalikan dana pada jaringan pembayaran.",
  ],
  [
    "Apa bedanya status pembayaran dan risiko?",
    "Status pembayaran menunjukkan apakah dana berhasil masuk. Risiko membantu menentukan pembayaran mana yang perlu diperiksa lebih dulu.",
  ],
  [
    "Apakah skor risiko adalah probabilitas fraud?",
    "Tidak. Skor membantu menentukan pembayaran yang perlu diperiksa. Hasilnya bukan jaminan transaksi bebas penipuan.",
  ],
  [
    "Apakah Graph membuktikan fraud?",
    "Tidak. Hubungan pembayaran hanya membantu melihat pola. Analyst tetap memeriksa bukti dan konteks.",
  ],
  [
    "Apakah semua fitur sudah siap digunakan?",
    "Belum. Fitur pola pembayaran dan pembelajaran bersama masih berupa contoh untuk demo, bukan sistem produksi.",
  ],
];

export default function HelpPage() {
  const [search, setSearch] = useState("");
  const filtered = useMemo(
    () =>
      faq.filter((item) =>
        item.join(" ").toLowerCase().includes(search.toLowerCase()),
      ),
    [search],
  );
  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <PageHeader
        title="Pusat Bantuan"
        description="Pelajari cara memeriksa pembayaran dan batas kemampuan FinGraph Mode Demo."
      />
      <div className="rounded-xl bg-primary px-5 py-6 text-primary-foreground sm:px-8 sm:py-8">
        <div className="mx-auto max-w-xl text-center">
          <CircleHelp className="mx-auto h-7 w-7" />
          <h2 className="mt-3 text-xl font-medium">
            Ada yang ingin ditanyakan?
          </h2>
          <div className="relative mt-5">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cari bantuan…"
              aria-label="Cari bantuan"
              className="h-12 w-full rounded-xl bg-surface pl-11 pr-4 text-sm text-foreground outline-none ring-offset-2 focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      </div>
      <section>
        <h2 className="font-medium">Panduan cepat</h2>
        <div className="mt-3 divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface">
          {guides.map((guide) => (
            <Link
              key={guide.title}
              href={guide.href}
              className="group flex min-h-24 items-center gap-4 px-5 py-4 hover:bg-surface-subtle"
            >
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-surface-subtle text-primary">
                <guide.icon className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <strong className="text-sm">{guide.title}</strong>
                <span className="mt-1 block text-sm leading-5 text-muted-foreground">
                  {guide.body}
                </span>
              </span>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          ))}
        </div>
      </section>
      <section>
        <h2 className="font-medium">Sumber data Mode Demo</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {[
            ["Pembayaran", "Simulator pembayaran lokal; bukan jaringan QRIS nyata."],
            ["Pesanan dan QRIS", "Profil merchant, outlet, dan QRIS contoh di database lokal."],
            ["Pemeriksaan pola", "Data contoh dengan beberapa skenario; bukan data bank produksi."],
            ["Pembelajaran bersama", "Contoh cara beberapa pihak belajar bersama tanpa mengirim data mentah."],
          ].map(([title, body]) => (
            <article key={title} className="rounded-xl border bg-surface p-4">
              <h3 className="text-sm font-medium">{title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{body}</p>
            </article>
          ))}
        </div>
      </section>
      <section>
        <h2 className="font-medium">Pertanyaan umum</h2>
        <Accordion
          className="mt-3 overflow-hidden rounded-xl border border-border bg-surface px-5"
          type="multiple"
        >
          {filtered.map(([question, answer]) => (
            <AccordionItem key={question} value={question}>
              <AccordionTrigger className="min-h-14 text-left text-sm font-medium">
                {question}
              </AccordionTrigger>
              <AccordionContent className="pb-5 text-sm leading-6 text-muted-foreground">
                {answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
        {!filtered.length && (
          <p className="rounded-xl border border-border bg-surface p-8 text-center text-sm text-muted-foreground">
            Tidak ada panduan yang cocok dengan pencarian.
          </p>
        )}
      </section>
      <section className="flex items-center gap-4 rounded-xl border border-border bg-surface-subtle p-5">
        <Store className="h-5 w-5 shrink-0 text-primary" />
        <div>
          <p className="font-medium">Tentang Mode Demo</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Data pembayaran dan penyedia pada aplikasi ini bersifat simulasi.
            Jangan gunakan sebagai konfirmasi transaksi QRIS nyata.
          </p>
        </div>
      </section>
    </div>
  );
}
