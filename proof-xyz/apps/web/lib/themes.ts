// Three distinct, modern theme containers. Each maps to CSS custom properties
// applied to the page root, so cards and chrome restyle wholesale. --bg may be
// a gradient string.

export interface Theme {
  id: string;
  label: string;
  description: string;
  vars: Record<string, string>;
  cardClass: string; // structural feel for cards
  fontClass: string; // heading/display font for this theme
}

export const THEMES: Theme[] = [
  {
    id: "midnight",
    label: "Midnight",
    description: "Premium dark with an electric indigo accent.",
    vars: {
      "--bg":
        "radial-gradient(900px 520px at 50% -8%, #1b1f30 0%, #0c0e16 58%, #08090f 100%)",
      "--surface": "rgba(23,26,38,0.92)",
      "--ink": "#eef1f8",
      "--muted": "#8b92a6",
      "--accent": "#7c6cff",
      "--chip": "rgba(124,108,255,0.16)",
      "--chip-ink": "#c4bcff",
    },
    cardClass:
      "rounded-3xl border border-white/10 shadow-[0_30px_70px_-30px_rgba(0,0,0,0.85)] backdrop-blur-sm",
    fontClass: "font-display",
  },
  {
    id: "paper",
    label: "Paper",
    description: "Clean editorial light with a crisp blue accent.",
    vars: {
      "--bg": "linear-gradient(180deg, #fafaf8 0%, #eef0f4 100%)",
      "--surface": "#ffffff",
      "--ink": "#15171d",
      "--muted": "#6b7280",
      "--accent": "#3b5bff",
      "--chip": "#eef1ff",
      "--chip-ink": "#2c45e0",
    },
    cardClass:
      "rounded-3xl border border-black/[0.07] shadow-[0_24px_50px_-26px_rgba(20,24,40,0.35)]",
    fontClass: "font-serif",
  },
  {
    id: "sunset",
    label: "Sunset",
    description: "Warm gradient with an energetic coral accent.",
    vars: {
      "--bg": "linear-gradient(160deg, #fff2ec 0%, #ffe1dd 48%, #ffe8d4 100%)",
      "--surface": "rgba(255,255,255,0.88)",
      "--ink": "#2a1a16",
      "--muted": "#9a7d72",
      "--accent": "#fb5d3b",
      "--chip": "#ffe1d6",
      "--chip-ink": "#c23a22",
    },
    cardClass:
      "rounded-3xl border border-[var(--accent)]/18 shadow-[0_26px_55px_-24px_rgba(251,93,59,0.5)] backdrop-blur-sm",
    fontClass: "font-display",
  },
];

export function getTheme(id: string): Theme {
  return THEMES.find((t) => t.id === id) ?? THEMES[0];
}
