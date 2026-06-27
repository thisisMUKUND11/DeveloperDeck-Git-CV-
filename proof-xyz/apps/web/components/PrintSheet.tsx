import type { Profile } from "@/lib/api";
import { BRAND, BRAND_TAGLINE } from "@/lib/brand";
import { getTheme } from "@/lib/themes";

// Print-only report. Tight, neatly-margined one-pager — every public project
// laid out as a compact report entry, light and ink-friendly regardless of the
// on-screen theme. Shown only when printing (see globals.css @media print).
export function PrintSheet({ profile }: { profile: Profile }) {
  const accent = getTheme(profile.theme).vars["--accent"] ?? "#3b5bff";
  const cards = profile.cards.filter((c) => !c.locked);

  const metaParts = [
    `github.com/${profile.username}`,
    `${profile.public_count} repos`,
    `${profile.language_count} languages`,
  ];
  if (profile.total_stars > 0) metaParts.push(`${profile.total_stars}★`);

  return (
    <div className="print-sheet hidden text-black print:block">
      {/* ---- Header ---- */}
      <header style={{ borderBottom: `2px solid ${accent}` }} className="pb-3">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="text-[22px] font-bold leading-tight">
            {profile.name || `@${profile.username}`}
          </h1>
          <span className="text-[10px] uppercase tracking-widest text-gray-400">
            {BRAND}
          </span>
        </div>
        {profile.headline && (
          <p className="text-[13px] font-semibold" style={{ color: accent }}>
            {profile.headline}
          </p>
        )}
        {profile.pitch && (
          <p className="mt-1 text-[11.5px] leading-snug text-gray-700">{profile.pitch}</p>
        )}
        <p className="mt-1.5 text-[10px] text-gray-500">{metaParts.join("  ·  ")}</p>
        {profile.top_skills.length > 0 && (
          <p className="mt-0.5 text-[10px] font-medium text-gray-600">
            {profile.top_skills.join("  ·  ")}
          </p>
        )}
      </header>

      {/* ---- Projects ---- */}
      <h2
        className="mt-4 text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400"
        style={{ breakAfter: "avoid" }}
      >
        Selected work
      </h2>

      <div className="mt-2">
        {cards.map((c) => (
          <article
            key={c.repo}
            className="border-b border-gray-200 py-2.5"
            style={{ breakInside: "avoid" }}
          >
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-mono text-[13px] font-bold">{c.repo}</h3>
              <span className="shrink-0 text-[10px] text-gray-500">{c.stat}</span>
            </div>
            {c.summary && (
              <p className="text-[11.5px] font-medium leading-snug">{c.summary}</p>
            )}

            <div className="mt-1.5 grid grid-cols-2 gap-x-5 gap-y-1">
              {c.why.length > 0 && (
                <div>
                  <p className="text-[8.5px] font-bold uppercase tracking-wider" style={{ color: accent }}>
                    Why
                  </p>
                  <ul className="ml-3.5 list-disc text-[10.5px] leading-snug text-gray-800">
                    {c.why.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
              {c.how.length > 0 && (
                <div>
                  <p className="text-[8.5px] font-bold uppercase tracking-wider" style={{ color: accent }}>
                    How
                  </p>
                  <ul className="ml-3.5 list-disc text-[10.5px] leading-snug text-gray-800">
                    {c.how.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <p className="mt-1 text-[9.5px] text-gray-500">
              {[c.languages.join(", "), c.url].filter(Boolean).join("  ·  ")}
            </p>
          </article>
        ))}
      </div>

      <footer className="mt-3 text-center text-[9px] text-gray-400">
        {BRAND} — {BRAND_TAGLINE}
      </footer>
    </div>
  );
}
