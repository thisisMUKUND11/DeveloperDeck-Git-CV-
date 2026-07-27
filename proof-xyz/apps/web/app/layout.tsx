import type { Metadata } from "next";
import { Fraunces, Inter, Space_Grotesk } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { MotionProvider } from "@/components/MotionProvider";
import { AUTHOR, AUTHOR_URL, BRAND_FULL } from "@/lib/brand";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

// Display: geometric, confident — headlines and card titles.
const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});
// Body: highly legible UI text.
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
// Serif: editorial flourish for the cinematic theme.
const serif = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
});

const DESCRIPTION =
  "Turn your GitHub into a swipeable, recruiter-ready proof-of-work portfolio in seconds.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: BRAND_FULL,
  description: DESCRIPTION,
  applicationName: BRAND_FULL,
  authors: [{ name: AUTHOR, url: AUTHOR_URL }],
  creator: AUTHOR,
  keywords: [
    "developer portfolio",
    "GitHub portfolio",
    "proof of work",
    "recruiter",
    "resume",
    "swipeable portfolio",
    BRAND_FULL,
  ],
  robots: { index: true, follow: true },
  verification: { google: "vrtfRuSYfI7hKCOebynlG1gLvv43wAJI1YQe4t6G6xk" },
  openGraph: {
    type: "website",
    siteName: BRAND_FULL,
    url: SITE_URL,
    title: BRAND_FULL,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: BRAND_FULL,
    description: DESCRIPTION,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable} ${serif.variable}`}
    >
      <body className="font-body antialiased">
        <MotionProvider>{children}</MotionProvider>
        <Analytics />
      </body>
    </html>
  );
}
