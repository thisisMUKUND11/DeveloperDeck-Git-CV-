import type { Metadata } from "next";
import Link from "next/link";

import { ThemedShell } from "@/components/ThemedShell";
import { AUTHOR_EMAIL, BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `Privacy & data — ${BRAND}`,
  description: `What ${BRAND} reads from GitHub, what it stores, and how to have a profile removed.`,
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-lg font-bold text-[var(--ink)]">{title}</h2>
      <div className="flex flex-col gap-3 text-sm leading-relaxed text-[var(--muted)]">
        {children}
      </div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <ThemedShell>
      <div className="flex w-full max-w-2xl flex-col gap-10">
        <div className="flex flex-col gap-2">
          <Link
            href="/"
            className="text-xs font-semibold text-[var(--accent)] underline-offset-4 hover:underline"
          >
            ← Back to {BRAND}
          </Link>
          <h1 className="font-display text-3xl font-bold text-[var(--ink)]">
            Privacy &amp; data
          </h1>
          <p className="text-sm text-[var(--muted)]">
            Plain English, no legalese. {BRAND} works entirely from data GitHub
            already publishes.
          </p>
        </div>

        <Section title="What we read">
          <p>
            When a reel is generated for a GitHub username, we call GitHub&apos;s
            public REST API and read: the public profile (name, bio, avatar,
            follower count), and for the top repositories ranked by stars and
            recency — the description, star and fork counts, languages, topics,
            the README, and dependency manifests such as{" "}
            <code className="font-mono text-xs">package.json</code> or{" "}
            <code className="font-mono text-xs">requirements.txt</code>.
          </p>
          <p>
            Dependencies are matched against a fixed lookup table to infer skill
            tags. We never clone repositories or read source files beyond those
            manifests and the README.
          </p>
        </Section>

        <Section title="Anyone can generate a reel for a public username">
          <p>
            This is deliberate — it lets a recruiter look up a candidate without
            waiting for a link. It also means a reel about you may exist without
            you creating it. Everything in it comes from your public GitHub
            profile and nothing else, but you can have it removed at any time
            (see below).
          </p>
        </Section>

        <Section title="Private repositories">
          <p>
            Private repositories are only ever read if you personally connect
            with GitHub and grant access. Even then they are shown as locked
            cards: the name is never displayed, no description, no code, no
            summary. They exist purely as a count. Your access token is used for
            that one request and is never written to our database.
          </p>
        </Section>

        <Section title="What we store">
          <p>
            A generated profile — the same public facts above plus the
            AI-written summaries — is stored so the page loads quickly and so a
            shared link keeps working. Profiles are regenerated when older than
            24 hours.
          </p>
          <p>
            When you create a share link we store a snapshot of only the
            projects you selected, plus a count of how many times that link has
            been opened. We do not store IP addresses, and there are no
            accounts, passwords, or tracking cookies.
          </p>
        </Section>

        <Section title="Third parties">
          <p>
            Repository text is sent to <strong>Google Gemini</strong> to write
            the card summaries. Hosting is <strong>Vercel</strong> (web) and{" "}
            <strong>Render</strong> (API), with a managed Postgres database.
            Anonymous, cookieless page-view counts come from Vercel Analytics.
          </p>
        </Section>

        <Section title="Removing your profile">
          <p>
            If you have a stored profile you can delete it — along with every
            share link made from it — by connecting with GitHub, which proves
            you own the account.
          </p>
          <p>
            You can also email{" "}
            <a
              href={`mailto:${AUTHOR_EMAIL}?subject=DevReel%20removal%20request`}
              className="font-semibold text-[var(--accent)] underline-offset-4 hover:underline"
            >
              {AUTHOR_EMAIL}
            </a>{" "}
            from any address and ask for a username to be removed. Deletion is
            permanent and takes effect immediately. Note that a reel can be
            regenerated by anyone afterwards, since it is built from public
            data — making your GitHub repositories private is the only way to
            prevent that.
          </p>
        </Section>

        <p className="text-xs text-[var(--muted)]/70">
          Questions about any of this? Email {AUTHOR_EMAIL}.
        </p>
      </div>
    </ThemedShell>
  );
}
