"use client";

import Link from "next/link";

import type { Profile } from "@/lib/api";
import { BRAND, BRAND_TAGLINE } from "@/lib/brand";
import { getTheme } from "@/lib/themes";
import { CardStack } from "./CardStack";
import { Credit } from "./Credit";
import { IdentityPanel } from "./IdentityPanel";
import { IntroCard } from "./IntroCard";
import { PrintSheet } from "./PrintSheet";
import { ProofCard } from "./ProofCard";
import { SharePanel } from "./SharePanel";

export function ProfileView({
  profile,
  readOnly = false,
}: {
  profile: Profile;
  readOnly?: boolean;
}) {
  const theme = getTheme(profile.theme);
  const hasCards = profile.cards.length > 0;

  const privateNote = !readOnly && !profile.private_access && (
    <p className="max-w-sm text-[11px] leading-relaxed text-[var(--muted)]">
      🔒 Private repositories aren’t shown — GitHub only reveals them with a
      <span className="font-mono"> repo</span>-scoped token on your own account.
    </p>
  );

  const pdfButton = (
    <button
      onClick={() => window.print()}
      className="rounded-full border border-[var(--ink)]/20 px-4 py-1.5 text-xs font-medium text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
    >
      ⤓ Save as PDF
    </button>
  );

  const footer = (
    <footer className="flex flex-col gap-1 text-xs text-[var(--muted)]">
      <span>
        {readOnly ? "Shared via " : ""}
        <span className="font-semibold text-[var(--ink)]">{BRAND}</span> —{" "}
        {BRAND_TAGLINE}
      </span>
      <Credit />
    </footer>
  );

  // Top navigation: a visible way back home, plus a restyled "make your own" CTA.
  const topNav = (
    <nav className="mb-7 flex w-full max-w-6xl items-center justify-between print:hidden">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 font-display text-sm font-semibold text-[var(--ink)] transition hover:text-[var(--accent)]"
      >
        <span aria-hidden className="text-base">
          ←
        </span>
        {BRAND}
      </Link>
      <Link
        href="/"
        className="rounded-full bg-[var(--accent)] px-4 py-2 font-display text-sm font-semibold text-white shadow-md shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-95"
      >
        ✦ Make your own
      </Link>
    </nav>
  );

  const emptyState = (
    <div
      className={`flex h-[300px] w-full max-w-[380px] flex-col items-center justify-center gap-3 text-center ${theme.cardClass} bg-[var(--surface)] p-8`}
    >
      <span className="text-4xl">🪺</span>
      <p className="font-display text-lg font-bold">No public builds yet</p>
      <p className="text-sm text-[var(--muted)]">
        When @{profile.username} pushes public repositories, they’ll show up here.
      </p>
    </div>
  );

  return (
    <main
      className="proof-root flex flex-col items-center px-6 py-10 lg:px-10"
      style={theme.vars as React.CSSProperties}
    >
      {/* Print-only one-pager (hidden on screen). */}
      <PrintSheet profile={profile} />

      {/* Top navigation — visible back-to-home + make-your-own CTA. */}
      {topNav}

      {/* ===== Mobile / tablet: centered column with the swipe deck ===== */}
      <div className="flex w-full max-w-md flex-col items-center gap-6 lg:hidden print:hidden">
        <header className="animate-fade-up flex flex-col items-center gap-2 text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--muted)]">
            @{profile.username}
          </p>
        </header>

        {privateNote && <div className="-mt-2 text-center">{privateNote}</div>}

        {!readOnly && (
          <SharePanel username={profile.username} cards={profile.cards} theme={profile.theme} />
        )}

        {hasCards ? (
          <CardStack
            slides={[
              <IntroCard key="intro" profile={profile} theme={theme} />,
              ...profile.cards.map((c) => <ProofCard key={c.repo} card={c} theme={theme} />),
            ]}
          />
        ) : (
          emptyState
        )}

        {pdfButton}
        <div className="text-center">{footer}</div>
      </div>

      {/* ===== Desktop: sticky identity sidebar + project grid ===== */}
      <div className="hidden w-full max-w-6xl gap-12 lg:grid lg:grid-cols-[320px_minmax(0,1fr)] print:hidden">
        <aside className="proof-scroll animate-fade-up sticky top-10 flex max-h-[calc(100dvh-4rem)] flex-col gap-6 overflow-y-auto pr-1">
          <IdentityPanel profile={profile} theme={theme} />
          {privateNote}
          {!readOnly && (
            <SharePanel username={profile.username} cards={profile.cards} theme={profile.theme} />
          )}
          {pdfButton}
          {footer}
        </aside>

        <section>
          {hasCards ? (
            <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-2 min-[1600px]:grid-cols-3">
              {profile.cards.map((c) => (
                <ProofCard key={c.repo} card={c} theme={theme} variant="grid" />
              ))}
            </div>
          ) : (
            emptyState
          )}
        </section>
      </div>
    </main>
  );
}
