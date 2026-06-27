import { ImageResponse } from "next/og";

import { BRAND, BRAND_TAGLINE } from "@/lib/brand";
import { getShareServer, ogTheme } from "@/lib/server";

export const alt = "Proof-of-work portfolio";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Rich preview image shown when a /s/<token> link is pasted in LinkedIn,
// Slack, WhatsApp, iMessage, etc.
// NOTE: Satori (the renderer) requires every <div> with >1 child to set
// display:flex, and treats interpolated text as multiple children — so any
// div with mixed text/expressions uses a single template-literal string.
export default async function Image({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const profile = await getShareServer(token);
  const t = ogTheme(profile?.theme ?? "midnight");

  const name = profile?.headline || profile?.name || profile?.username || BRAND;
  const skills = (profile?.top_skills ?? []).slice(0, 4);
  const repos = profile?.public_count ?? 0;
  const langs = profile?.language_count ?? 0;
  const handle = profile?.username ? `@${profile.username}` : "";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: t.bg,
          color: t.ink,
          padding: "70px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ width: 18, height: 18, borderRadius: 999, background: t.accent, display: "flex" }} />
          <div style={{ fontSize: 30, fontWeight: 700, display: "flex" }}>{BRAND}</div>
          <div style={{ fontSize: 24, color: t.muted, display: "flex" }}>
            {`— ${BRAND_TAGLINE}`}
          </div>
          {handle && (
            <div style={{ fontSize: 24, color: t.muted, display: "flex" }}>{`· ${handle}`}</div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ fontSize: 64, fontWeight: 800, lineHeight: 1.05, display: "flex" }}>
            {name}
          </div>
          {profile?.pitch && (
            <div style={{ fontSize: 30, color: t.muted, lineHeight: 1.3, maxWidth: 980, display: "flex" }}>
              {profile.pitch}
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: "12px" }}>
            {skills.map((s) => (
              <div
                key={s}
                style={{
                  display: "flex",
                  fontSize: 24,
                  color: t.accent,
                  border: `2px solid ${t.accent}`,
                  borderRadius: 999,
                  padding: "8px 20px",
                }}
              >
                {s}
              </div>
            ))}
          </div>
          <div style={{ fontSize: 28, color: t.muted, display: "flex" }}>
            {`${repos} repos · ${langs} langs`}
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
