import { BRAND } from "@/lib/brand";

const STEPS: { icon: string; title: string; body: string }[] = [
  {
    icon: "🔗",
    title: "Drop your GitHub handle",
    body: "Just your username — no sign-up, no setup. Or connect with GitHub for private repos.",
  },
  {
    icon: "✨",
    title: "We read your real work",
    body: "Languages, dependencies and READMEs across your top repos — then AI writes a crisp highlight for each.",
  },
  {
    icon: "🎴",
    title: "Swipe, theme, and share",
    body: "Get a swipeable deck of your best projects. Pick what to show, then share one link or a QR code.",
  },
];

const USES: { icon: string; title: string; body: string }[] = [
  {
    icon: "📄",
    title: "On your résumé",
    body: "Paste the link or drop the QR code. A recruiter scans it and instantly swipes through your real projects — no logins, no digging through GitHub.",
  },
  {
    icon: "💼",
    title: "LinkedIn & portfolio",
    body: "One link that proves what you've actually built, not just what you list. Great as your featured link or in a post.",
  },
  {
    icon: "📨",
    title: "Job applications",
    body: "Stand out from plain-text resumes with an interactive, mobile-first glimpse of your work in about 15 seconds.",
  },
  {
    icon: "⚡",
    title: "Quick to skim",
    body: "You choose exactly which public repos appear, each with a one-line hook — so the best of your work reads at a glance.",
  },
];

/** Home-page explainer: how the flow works, and where the link/QR is useful.
 *  Theme-aware (inherits the page's CSS variables). */
export function UseCases() {
  return (
    <section
      id="how-it-works"
      className="mt-24 flex w-full max-w-4xl scroll-mt-8 flex-col gap-14"
    >
      {/* How it works */}
      <div className="flex flex-col gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
            How it works
          </span>
          <h2 className="font-display text-2xl font-bold text-[var(--ink)] sm:text-3xl">
            From GitHub to a shareable reel in seconds
          </h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <div
              key={s.title}
              className="relative flex flex-col gap-3 rounded-2xl border border-[var(--ink)]/10 bg-[var(--surface)] p-5"
            >
              <span className="absolute right-4 top-4 font-mono text-xs text-[var(--muted)]">
                0{i + 1}
              </span>
              <span className="text-2xl">{s.icon}</span>
              <h3 className="font-display text-base font-bold text-[var(--ink)]">
                {s.title}
              </h3>
              <p className="text-sm leading-relaxed text-[var(--muted)]">{s.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Where to use it */}
      <div className="flex flex-col gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
            Where to use it
          </span>
          <h2 className="font-display text-2xl font-bold text-[var(--ink)] sm:text-3xl">
            One link. One QR. Everywhere you apply.
          </h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {USES.map((u) => (
            <div
              key={u.title}
              className="flex gap-4 rounded-2xl border border-[var(--ink)]/10 bg-[var(--surface)] p-5"
            >
              <span className="text-2xl">{u.icon}</span>
              <div className="flex flex-col gap-1.5">
                <h3 className="font-display text-base font-bold text-[var(--ink)]">
                  {u.title}
                </h3>
                <p className="text-sm leading-relaxed text-[var(--muted)]">{u.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Back-to-top nudge */}
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-sm text-[var(--muted)]">
          Ready? Roll your own {BRAND} in about 15 seconds.
        </p>
        <a
          href="#top"
          className="rounded-full bg-[var(--accent)] px-6 py-3 font-display text-sm font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-95"
        >
          ↑ Try it now
        </a>
      </div>
    </section>
  );
}
