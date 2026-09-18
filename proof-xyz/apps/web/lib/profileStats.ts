import type { Profile } from "./api";

export interface Stat {
  value: string;
  label: string;
}

/** 1200 -> "1.2k", 1000 -> "1k". */
export function compact(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace(".0", "")}k` : `${n}`;
}

/** The hero stat row, shared by the mobile IntroCard and the desktop
 *  IdentityPanel so the two can't drift apart. Stars are omitted at zero
 *  rather than shown as "0★", which reads as a negative. */
export function profileStats(profile: Profile): Stat[] {
  const stats: Stat[] = [
    {
      value: `${profile.public_count}`,
      label: profile.public_count === 1 ? "repo" : "repos",
    },
    { value: `${profile.language_count}`, label: "langs" },
  ];
  if (profile.total_stars > 0) {
    stats.push({ value: `${compact(profile.total_stars)}★`, label: "stars" });
  }
  return stats;
}
