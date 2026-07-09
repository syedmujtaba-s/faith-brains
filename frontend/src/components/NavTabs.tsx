"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Ask" },
  { href: "/quran", label: "Quran" },
  { href: "/hadith", label: "Hadith" },
  { href: "/learn", label: "Learn" },
  { href: "/saved", label: "Saved" },
];

export default function NavTabs() {
  const pathname = usePathname();
  return (
    <nav className="-mb-px flex gap-1 overflow-x-auto" aria-label="Sections">
      {TABS.map((tab) => {
        const active = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm tracking-wide transition-colors ${
              active
                ? "border-gold text-goldsoft"
                : "border-transparent text-mist hover:text-snow"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
