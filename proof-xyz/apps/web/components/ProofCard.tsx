import type { Card } from "@/lib/api";
import type { Theme } from "@/lib/themes";

function Badge({ visibility }: { visibility: "public" | "private" }) {
  const isPrivate = visibility === "private";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${
        isPrivate
          ? "bg-[var(--muted)]/20 text-[var(--muted)]"
          : "bg-[var(--accent)]/15 text-[var(--accent)]"
      }`}
    >
      {isPrivate ? "🔒 Private" : "● Public"}
    </span>
  );
}

function Section({ label, points }: { label: string; points: string[] }) {
  if (!points || points.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--accent)]">
        {label}
      </span>
      <ul className="flex flex-col gap-2">
        {points.map((point, i) => (
          <li key={i} className="flex gap-2.5">
            <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]" />
            <span className="text-[14.5px] leading-relaxed text-[var(--ink)] [text-align:justify]">
              {point}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ProofCard({ card, theme }: { card: Card; theme: Theme }) {
  return (
    <div
      className={`flex h-full w-full flex-col bg-[var(--surface)] ${theme.cardClass} ${theme.fontClass}`}
    >
      {/* Fixed header — never scrolls, never overlapped. */}
      <div className="flex items-start justify-between gap-3 border-b border-[var(--ink)]/10 p-6 pb-4">
        <div className="flex min-w-0 flex-col gap-2">
          <span className="truncate font-mono text-sm font-bold text-[var(--ink)]">
            {card.repo}
          </span>
          <Badge visibility={card.visibility} />
        </div>
        {!card.locked && card.stat && (
          <span className="shrink-0 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-bold text-white">
            {card.stat}
          </span>
        )}
      </div>

      {/* Scrollable body — overflow stays inside the card, so content can't
          spill over the chrome or the next card. */}
      <div className="proof-scroll flex-1 overflow-y-auto p-6 pt-4">
        {card.locked ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <span className="text-3xl">🔒</span>
            <p className="text-sm text-[var(--muted)]">
              This repository is private — its details aren’t shown publicly.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {card.summary && (
              <h2 className="text-xl font-bold leading-tight text-[var(--ink)]">
                {card.summary}
              </h2>
            )}
            <Section label="The why" points={card.why} />
            <Section label="Under the hood" points={card.how} />

            {card.languages.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--accent)]">
                  Languages
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {card.languages.map((lang) => (
                    <span
                      key={lang}
                      className="rounded-md bg-[var(--chip)] px-2 py-0.5 text-xs font-medium text-[var(--chip-ink)]"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {card.skills.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--accent)]">
                  Skills
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {card.skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full border border-[var(--accent)]/30 px-2.5 py-0.5 text-xs font-medium text-[var(--ink)]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Fixed footer link. */}
      {card.url && (
        <div className="border-t border-[var(--ink)]/10 p-4">
          <a
            href={card.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-[var(--accent)] underline-offset-4 hover:underline"
            onPointerDownCapture={(e) => e.stopPropagation()}
          >
            {card.locked ? "Request access →" : "View repository →"}
          </a>
        </div>
      )}
    </div>
  );
}
