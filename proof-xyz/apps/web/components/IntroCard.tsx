import type { Profile } from "@/lib/api";
import type { Theme } from "@/lib/themes";

function compact(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace(".0", "")}k` : `${n}`;
}

/** The TL;DR intro slide — the 6-second pitch shown first. */
export function IntroCard({ profile, theme }: { profile: Profile; theme: Theme }) {
  const stats: { value: string; label: string }[] = [
    { value: `${profile.public_count}`, label: profile.public_count === 1 ? "repo" : "repos" },
    { value: `${profile.language_count}`, label: "langs" },
  ];
  if (profile.total_stars > 0)
    stats.push({ value: `${compact(profile.total_stars)}★`, label: "stars" });

  return (
    <div
      className={`proof-scroll flex h-full w-full flex-col overflow-y-auto bg-[var(--surface)] ${theme.cardClass} ${theme.fontClass}`}
    >
      {/* m-auto centres the block when there's room, and lets it scroll
          (instead of overflowing onto the controls below) when there isn't. */}
      <div className="m-auto flex flex-col items-center gap-4 p-7 text-center">
        {profile.avatar_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={profile.avatar_url}
            alt={profile.username}
            className="h-16 w-16 rounded-full border-2 border-[var(--accent)] object-cover"
          />
        )}

      <div className="flex flex-col items-center gap-1">
        <span className="font-mono text-xs uppercase tracking-widest text-[var(--muted)]">
          @{profile.username}
        </span>
        <h2 className="text-2xl font-bold leading-tight text-[var(--ink)]">
          {profile.headline || profile.name || profile.username}
        </h2>
      </div>

      {profile.pitch && (
        <p className="max-w-[18rem] text-[15px] leading-relaxed text-[var(--muted)]">
          {profile.pitch}
        </p>
      )}

      {/* Hero stat row */}
      <div className="flex items-stretch gap-4">
        {stats.map((s, i) => (
          <div key={s.label} className="flex items-center gap-4">
            {i > 0 && <span className="h-8 w-px bg-[var(--ink)]/15" />}
            <div className="flex flex-col">
              <span className="text-2xl font-bold leading-none text-[var(--accent)]">
                {s.value}
              </span>
              <span className="mt-1 text-[11px] uppercase tracking-wide text-[var(--muted)]">
                {s.label}
              </span>
            </div>
          </div>
        ))}
      </div>

      {profile.top_skills.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {profile.top_skills.slice(0, 5).map((s) => (
            <span
              key={s}
              className="rounded-full bg-[var(--chip)] px-3 py-1 text-xs font-medium text-[var(--chip-ink)]"
            >
              {s}
            </span>
          ))}
        </div>
      )}

        <span className="mt-1 text-xs text-[var(--muted)]">
          Swipe to explore {profile.public_count}{" "}
          {profile.public_count === 1 ? "project" : "projects"} →
        </span>
      </div>
    </div>
  );
}
