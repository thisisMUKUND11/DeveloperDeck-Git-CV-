import Link from "next/link";

import { ThemedShell } from "@/components/ThemedShell";
import { BRAND } from "@/lib/brand";

export default function NotFound() {
  return (
    <ThemedShell>
      <div className="flex max-w-md flex-1 flex-col items-center justify-center gap-5 text-center">
        <span className="font-mono text-xs uppercase tracking-[0.25em] text-[var(--muted)]">
          404
        </span>
        <h1 className="font-display text-3xl font-bold text-[var(--ink)]">
          Nothing here yet
        </h1>
        <p className="text-[15px] leading-relaxed text-[var(--muted)]">
          This reel hasn&apos;t been generated, or the link has expired. Enter a
          GitHub username on the home page and {BRAND} will build one in about
          15 seconds.
        </p>
        <Link
          href="/"
          className="rounded-full bg-[var(--accent)] px-6 py-3 font-display text-sm font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-95"
        >
          Roll a reel →
        </Link>
      </div>
    </ThemedShell>
  );
}
