import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// robots.txt — allow crawling the public site, but keep unique share links
// (/s/<token>) out of search indexes since they're private résumé URLs.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/s/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
