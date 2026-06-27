import Link from "next/link";

import { ProfileView } from "@/components/ProfileView";
import { getProfileServer } from "@/lib/server";
import { getTheme } from "@/lib/themes";

export default async function ProfilePage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  const profile = await getProfileServer(username);

  if (!profile) {
    const theme = getTheme("neo-brutalist");
    return (
      <main
        className="proof-root flex flex-col items-center justify-center gap-6 px-6 text-center"
        style={theme.vars as React.CSSProperties}
      >
        <div className="animate-fade-up flex flex-col items-center gap-5">
          <span className="text-5xl">🔍</span>
          <div className="flex flex-col gap-2">
            <h1 className="font-display text-3xl font-bold">
              No deck yet for{" "}
              <span className="text-[var(--accent)]">@{username}</span>
            </h1>
            <p className="max-w-xs text-[var(--muted)]">
              This profile hasn’t been generated. Build it in ~30 seconds.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-2xl bg-[var(--accent)] px-6 py-3 font-display font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-[0.98]"
          >
            Generate {username}’s deck →
          </Link>
        </div>
      </main>
    );
  }

  return <ProfileView profile={profile} />;
}
