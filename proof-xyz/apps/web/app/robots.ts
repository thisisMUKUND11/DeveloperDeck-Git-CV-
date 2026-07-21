import type { MetadataRoute } from "next";

const BASE =
  process.env.NEXT_PUBLIC_PUBLIC_BASE_URL ||
  "https://developer-deck-git-cv.vercel.app";

// robots.txt — allow crawling the public site, but keep unique share links
// (/s/<token>) out of search indexes since they're private résumé URLs.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/s/"],
    },
    sitemap: `${BASE}/sitemap.xml`,
  };
}
