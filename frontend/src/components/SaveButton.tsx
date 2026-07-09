"use client";

import { useEffect, useState } from "react";
import { isSaved, toggleSaved, type SavedItem } from "@/lib/saved";

export default function SaveButton({
  item,
  onPaper = false,
}: {
  item: Omit<SavedItem, "savedAt">;
  onPaper?: boolean;
}) {
  const [saved, setSaved] = useState(false);
  useEffect(() => setSaved(isSaved(item.id)), [item.id]);

  return (
    <button
      type="button"
      onClick={() => setSaved(toggleSaved(item))}
      aria-pressed={saved}
      title={saved ? "Remove from Saved" : "Save"}
      className={`rounded-full p-1.5 transition-colors ${
        onPaper ? "text-paperfaint hover:text-paperink" : "text-mist hover:text-snow"
      }`}
    >
      <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" aria-hidden="true">
        <path
          d="M6 3.5h12a.5.5 0 0 1 .5.5v16.2a.3.3 0 0 1-.47.25L12 16.4l-6.03 4.05a.3.3 0 0 1-.47-.25V4a.5.5 0 0 1 .5-.5Z"
          fill={saved ? "var(--color-gold)" : "none"}
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
      <span className="sr-only">{saved ? "Remove from Saved" : "Save"}</span>
    </button>
  );
}
