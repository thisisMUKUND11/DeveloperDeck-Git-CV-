"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { BRAND, BRAND_TAGLINE } from "@/lib/brand";
import { THEMES, getTheme } from "@/lib/themes";
import { GenerateForm } from "./GenerateForm";

// Kinetic rotating noun in the headline — modern, not salesy.
const WORDS = ["pitch", "portfolio", "case study", "flex"];

export function Landing() {
  const [themeId, setThemeId] = useState(THEMES[0].id);
  const theme = getTheme(themeId);
  const [word, setWord] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setWord((w) => (w + 1) % WORDS.length), 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <main
      className="proof-root relative flex flex-col items-center justify-center px-6 py-16 transition-colors duration-500"
      style={theme.vars as React.CSSProperties}
    >
      {/* Soft dotted texture behind everything. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: "radial-gradient(var(--ink) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 35%, black 35%, transparent 100%)",
          opacity: 0.06,
        }}
      />

      {/* Themed accent glow behind the hero — recolours live with the theme. */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-16 h-80 w-80 -translate-x-1/2 rounded-full blur-[90px] transition-colors duration-500"
        style={{ background: "var(--accent)", opacity: 0.18 }}
      />

      <div className="relative flex w-full max-w-lg flex-col items-center gap-9 text-center">
        <div className="flex flex-col items-center gap-5">
          <div className="animate-fade-up flex flex-col items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/devreel-logo.png"
              alt={`${BRAND} logo`}
              className="h-20 w-20 rounded-[22px] object-cover shadow-[0_10px_40px_-10px_var(--accent)] ring-1 ring-white/10"
            />
            <div className="flex flex-col items-center gap-1">
              <span className="font-display text-xl font-bold tracking-tight text-[var(--ink)]">
                {BRAND}
              </span>
              <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
                {BRAND_TAGLINE}
              </span>
            </div>
          </div>

          <h1
            className="animate-fade-up font-display text-[2.6rem] font-bold leading-[1.05] sm:text-5xl md:text-[3.4rem]"
            style={{ animationDelay: "80ms" }}
          >
            Turn your GitHub
            <br />
            into a{" "}
            <span className="relative inline-block min-w-[6ch] text-left align-bottom">
              <AnimatePresence mode="wait">
                <motion.span
                  key={word}
                  initial={{ y: "0.5em", opacity: 0, filter: "blur(6px)" }}
                  animate={{ y: 0, opacity: 1, filter: "blur(0px)" }}
                  exit={{ y: "-0.5em", opacity: 0, filter: "blur(6px)" }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                  className="inline-block text-[var(--accent)]"
                >
                  {WORDS[word]}.
                </motion.span>
              </AnimatePresence>
            </span>
          </h1>

          <p
            className="animate-fade-up max-w-md text-[15px] leading-relaxed text-[var(--muted)]"
            style={{ animationDelay: "150ms" }}
          >
            We read your repositories — the languages, the dependencies, the
            READMEs — and turn them into a swipeable deck a recruiter actually
            finishes. In about 30 seconds.
          </p>
        </div>

        {/* Theme picker — restyles the whole home page live, and is the theme
            the generated profile starts in. */}
        <div
          className="animate-fade-up flex flex-col items-center gap-2"
          style={{ animationDelay: "220ms" }}
        >
          <span className="text-[11px] uppercase tracking-widest text-[var(--muted)]">
            Pick a vibe
          </span>
          <div className="flex flex-wrap justify-center gap-2">
            {THEMES.map((t) => (
              <button
                key={t.id}
                onClick={() => setThemeId(t.id)}
                className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition ${
                  themeId === t.id
                    ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]"
                    : "border-[var(--ink)]/20 text-[var(--muted)] hover:border-[var(--ink)]/45"
                }`}
              >
                <span
                  aria-hidden
                  className="h-2.5 w-2.5 rounded-full ring-1 ring-black/10"
                  style={{ background: t.vars["--accent"] }}
                />
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <GenerateForm theme={themeId} />

        <div
          className="animate-fade-up flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs font-medium text-[var(--muted)]"
          style={{ animationDelay: "320ms" }}
        >
          <span>● You choose what’s shared</span>
          <span>● AI-written</span>
          <span>● One link for your résumé</span>
        </div>
      </div>
    </main>
  );
}
