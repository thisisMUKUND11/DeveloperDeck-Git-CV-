import type { Config } from "tailwindcss";

// Theme colours live in CSS custom properties (see lib/themes.ts). Tailwind 3
// can't apply an opacity modifier to an arbitrary `[var(--x)]` value — classes
// like `border-[var(--ink)]/10` silently generate nothing. Registering each
// variable through color-mix() makes `border-ink/10`, `bg-accent/15`, etc. work.
const themed = (name: string) =>
  `color-mix(in srgb, var(--${name}) calc(<alpha-value> * 100%), transparent)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: themed("ink"),
        muted: themed("muted"),
        accent: themed("accent"),
        surface: themed("surface"),
        chip: themed("chip"),
        "chip-ink": themed("chip-ink"),
      },
      opacity: { 12: "0.12", 18: "0.18" },
      fontFamily: {
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "ui-serif", "serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.22,1,0.36,1) both",
        shimmer: "shimmer 1.4s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
