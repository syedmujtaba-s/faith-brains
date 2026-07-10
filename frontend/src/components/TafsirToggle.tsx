"use client";

import { useState } from "react";

type Tafsir = { source_key: string; source_name: string; language: string; text: string };

export default function TafsirToggle({ surah, ayah }: { surah: number; ayah: number }) {
  const [open, setOpen] = useState(false);
  const [tafsirs, setTafsirs] = useState<Tafsir[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && tafsirs === null && !loading) {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/quran/${surah}/${ayah}/tafsir`);
        setTafsirs(res.ok ? await res.json() : []);
      } catch {
        setTafsirs([]);
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={toggle}
        className="text-xs tracking-wide text-paperfaint underline decoration-gold/50 underline-offset-4 hover:text-paperink"
      >
        {open ? "Hide tafsir" : "Tafsir"}
      </button>
      {open && (
        <div className="mt-3 border-t border-paperline pt-3">
          {loading && <p className="text-xs text-paperfaint">Loading tafsir…</p>}
          {tafsirs?.length === 0 && (
            <p className="text-xs text-paperfaint">No tafsir available for this verse.</p>
          )}
          {tafsirs?.map((t) => (
            <div key={t.source_key}>
              <p className="mb-2 text-xs font-bold tracking-wide text-paperfaint">
                {t.source_name}
              </p>
              <div className="max-h-80 space-y-3 overflow-y-auto pr-2 font-serif text-sm leading-relaxed text-paperink/85">
                {t.text.split(/\n{2,}/).map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
