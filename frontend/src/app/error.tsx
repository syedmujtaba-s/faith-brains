"use client";

const isDev = process.env.NODE_ENV === "development";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-md py-20 text-center">
      <h2 className="font-display text-2xl text-snow">Couldn&apos;t load this page</h2>
      {isDev ? (
        <p className="mt-3 text-sm text-mist">
          The FaithBrains API may not be running. Start it with{" "}
          <code className="rounded bg-raise px-1.5 py-0.5 text-goldsoft">
            uv run uvicorn app.main:app
          </code>{" "}
          in <code className="rounded bg-raise px-1.5 py-0.5 text-goldsoft">backend/</code>, then
          try again.
        </p>
      ) : (
        <p className="mt-3 text-sm text-mist">
          Something went wrong on our side. Please try again in a moment.
        </p>
      )}
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded-full bg-gold px-6 py-2 text-sm font-bold text-ink"
      >
        Retry
      </button>
    </div>
  );
}
