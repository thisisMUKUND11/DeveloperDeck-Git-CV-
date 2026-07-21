import type { Metadata } from "next";
import { Fraunces, Inter, Space_Grotesk } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { BRAND_FULL } from "@/lib/brand";
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

const SITE_URL =
  process.env.NEXT_PUBLIC_PUBLIC_BASE_URL ||
  "https://developer-deck-git-cv.vercel.app";

const DESCRIPTION =
  "Turn your GitHub into a swipeable, recruiter-ready proof-of-work portfolio in seconds.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: BRAND_FULL,
  description: DESCRIPTION,
  applicationName: BRAND_FULL,
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
        {children}
        <Analytics />
      </body>
    </html>
  );
}
