import type { Metadata } from "next";
import { Fraunces, Inter, Space_Grotesk } from "next/font/google";
import { BRAND } from "@/lib/brand";
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

export const metadata: Metadata = {
  title: `${BRAND} — your work, on one link`,
  description:
    "Turn your GitHub into a swipeable, recruiter-ready proof-of-work portfolio.",
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
      <body className="font-body antialiased">{children}</body>
    </html>
  );
}
