import type { Metadata } from "next";
import { Alegreya, Alegreya_Sans, Amiri, Marcellus } from "next/font/google";
import Link from "next/link";
import NavTabs from "@/components/NavTabs";
import "./globals.css";

const marcellus = Marcellus({ weight: "400", subsets: ["latin"], variable: "--font-marcellus" });
const alegreya = Alegreya({ subsets: ["latin"], variable: "--font-alegreya" });
const alegreyaSans = Alegreya_Sans({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  variable: "--font-alegreya-sans",
});
const amiri = Amiri({ weight: ["400", "700"], subsets: ["arabic"], variable: "--font-amiri" });

export const metadata: Metadata = {
  title: "FaithBrains — Quran & Hadith companion",
  description:
    "Search the Quran and authentic Hadith, and ask questions answered strictly from cited sources. An educational tool — not a religious authority.",
};

function StarMark() {
  // Rub el Hizb — the 8-pointed star used in mushafs to mark divisions
  return (
    <svg viewBox="0 0 40 40" className="h-7 w-7" aria-hidden="true">
      <rect x="9" y="9" width="22" height="22" fill="none" stroke="var(--color-gold)" strokeWidth="1.6" />
      <rect
        x="9" y="9" width="22" height="22" fill="none" stroke="var(--color-gold)" strokeWidth="1.6"
        transform="rotate(45 20 20)"
      />
      <circle cx="20" cy="20" r="3" fill="var(--color-gold)" />
    </svg>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${marcellus.variable} ${alegreya.variable} ${alegreyaSans.variable} ${amiri.variable}`}>
      <body className="min-h-screen flex flex-col">
        <header className="border-b border-line">
          <div className="mx-auto max-w-5xl px-4">
            <div className="flex items-center justify-between gap-4 py-4">
              <Link href="/" className="flex items-center gap-3">
                <StarMark />
                <span className="font-display text-2xl tracking-wide text-snow">
                  Faith<span className="text-goldsoft">Brains</span>
                </span>
              </Link>
              <form action="/search" className="hidden sm:block">
                <input
                  type="search"
                  name="q"
                  placeholder="Search Quran & Hadith — try 2:255 or الصبر"
                  className="w-72 rounded-full border border-line bg-lapis px-4 py-1.5 text-sm text-snow placeholder:text-mist/70"
                />
              </form>
            </div>
            <NavTabs />
          </div>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>

        <footer className="border-t border-line py-8 text-center text-xs leading-relaxed text-mist">
          <div className="mx-auto max-w-3xl px-4 space-y-2">
            <p>
              Quran text: Tanzil Project (tanzil.net). Translations: Saheeh International and Rowwad
              Translation Center via QuranEnc.com (edition versions shown per translation). Hadith
              data: open hadith-api dataset.
            </p>
            <p className="text-goldsoft/80">
              FaithBrains is an educational tool and not a source of religious rulings. For personal
              guidance, consult a qualified scholar.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
