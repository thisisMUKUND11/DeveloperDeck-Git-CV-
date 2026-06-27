"use client";

import type { Profile } from "@/lib/api";
import { BRAND } from "@/lib/brand";
import { getTheme } from "@/lib/themes";
import { CardStack } from "./CardStack";
import { SharePanel } from "./SharePanel";

export function ProfileView({
  profile,
  readOnly = false,
}: {
  profile: Profile;
  readOnly?: boolean;
}) {
  // Theme is fixed to whatever was chosen on the home page (baked into the
  // profile at generation time). No picker on inner pages.
  const theme = getTheme(profile.theme);

  return (
    <main
      className="proof-root flex flex-col items-center px-6 py-10"
      style={theme.vars as React.CSSProperties}
    >
      <div className="flex w-full max-w-md flex-col items-center gap-6">
        <header className="animate-fade-up flex flex-col items-center gap-3 text-center">
          {profile.avatar_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={profile.avatar_url}
              alt={profile.username}
              className="h-16 w-16 rounded-full border-2 border-[var(--ink)]/15 object-cover"
            />
          )}
          <div className="flex flex-col items-center gap-1">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--muted)]">
              @{profile.username}
            </p>
            <h1 className={`text-2xl font-bold leading-tight ${theme.fontClass}`}>
              {profile.headline || profile.name || profile.username}
            </h1>
            <p className="text-xs text-[var(--muted)]">
              {profile.public_count} public
              {profile.private_count > 0 && ` · ${profile.private_count} private`} ·{" "}
              {profile.cards.length} shown
            </p>
          </div>
        </header>

        {!readOnly && !profile.private_access && (
          <p className="-mt-2 max-w-sm text-center text-[11px] leading-relaxed text-[var(--muted)]">
            🔒 Private repositories aren’t shown — GitHub only reveals them with a
            <span className="font-mono"> repo</span>-scoped token on your own account.
          </p>
        )}

        {!readOnly && (
          <SharePanel
            username={profile.username}
            cards={profile.cards}
            theme={profile.theme}
          />
        )}

        {profile.cards.length > 0 ? (
          <CardStack cards={profile.cards} theme={theme} />
        ) : (
          <div
            className={`flex h-[300px] w-full max-w-[380px] flex-col items-center justify-center gap-3 text-center ${theme.cardClass} bg-[var(--surface)] p-8`}
          >
            <span className="text-4xl">🪺</span>
            <p className="font-display text-lg font-bold">No public builds yet</p>
            <p className="text-sm text-[var(--muted)]">
              When @{profile.username} pushes public repositories, they’ll show up
              here as swipeable cards.
            </p>
          </div>
        )}

        <footer className="flex flex-col items-center gap-1 pt-2 text-center text-xs text-[var(--muted)]">
          {readOnly && <span>Shared via {BRAND}</span>}
          <a href="/" className="font-semibold text-[var(--accent)]">
            Build your own →
          </a>
        </footer>
      </div>
    </main>
  );
}
