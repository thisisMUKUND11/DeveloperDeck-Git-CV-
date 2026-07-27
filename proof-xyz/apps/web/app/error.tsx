"use client";

import { useEffect } from "react";

import { ThemedShell } from "@/components/ThemedShell";

/** Route-level error boundary. Without one, any thrown server-component error
 *  (a backend timeout, a cold-started API) shows Next's default grey page. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <ThemedShell>
      <div className="flex max-w-md flex-1 flex-col items-center justify-center gap-5 text-center">
        <span className="text-3xl">⚡</span>
        <h1 className="font-display text-3xl font-bold text-[var(--ink)]">
          That didn&apos;t load
        </h1>
        <p className="text-[15px] leading-relaxed text-[var(--muted)]">
          Something went wrong reaching our servers. If this is the first
          request in a while, the backend may still be waking up — try again in
          a few seconds.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={reset}
            className="rounded-full bg-[var(--accent)] px-6 py-3 font-display text-sm font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-95"
          >
            Try again
          </button>
          <a
            href="/"
            className="rounded-full border border-[var(--ink)]/20 px-6 py-3 font-display text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--ink)]/45"
          >
            Back home
          </a>
        </div>
        {error.digest && (
          <p className="font-mono text-[11px] text-[var(--muted)]/70">
            ref: {error.digest}
          </p>
        )}
      </div>
    </ThemedShell>
  );
}
