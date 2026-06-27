import Link from "next/link";

import { ProfileView } from "@/components/ProfileView";
import { getShare } from "@/lib/api";
import { getTheme } from "@/lib/themes";

export default async function SharedPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const profile = await getShare(token);

  if (!profile) {
    const theme = getTheme("neo-brutalist");
    return (
      <main
        className="proof-root flex flex-col items-center justify-center gap-6 px-6 text-center"
        style={theme.vars as React.CSSProperties}
      >
        <div className="animate-fade-up flex flex-col items-center gap-5">
          <span className="text-5xl">🔗</span>
          <div className="flex flex-col gap-2">
            <h1 className="font-display text-3xl font-bold">Link not found</h1>
            <p className="max-w-xs text-[var(--muted)]">
              This shared link is invalid or was replaced by a newer one.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-2xl bg-[var(--accent)] px-6 py-3 font-display font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-[0.98]"
          >
            Build your own →
          </Link>
        </div>
      </main>
    );
  }

  return <ProfileView profile={profile} readOnly />;
}
