import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Sitemap for search engines. Only the static public pages are listed —
// generated profiles (/<username>) and share links (/s/<token>) are dynamic
// and user-specific, so they're intentionally excluded.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/privacy`,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];
}
