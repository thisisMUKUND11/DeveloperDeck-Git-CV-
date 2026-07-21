"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { track } from "@vercel/analytics";

import { generateProfile } from "@/lib/api";
import { formMemory } from "@/lib/uiState";

const STEPS = [
  "Connecting to GitHub…",
  "Reading your top repositories…",
  "Parsing dependencies into skills…",
  "Writing your proof cards…",
  "Designing your deck…",
];

export function GenerateForm({ theme }: { theme: string }) {
  const router = useRouter();
  // Seed from UI memory so the handle persists across navigation (resets on refresh).
  const [username, setUsername] = useState(formMemory.username);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onUsernameChange = (value: string) => {
    formMemory.username = value;
    setUsername(value);
  };

  useEffect(() => {
    if (!loading) return;
    setStep(0);
    const id = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1300);
    return () => clearInterval(id);
  }, [loading]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const handle = username.trim().replace(/^@/, "");
    if (!handle) return;
    setLoading(true);
    setError(null);
    try {
      await generateProfile(handle, theme);
      // Count a real "used the app" action, distinct from a plain page visit.
      track("deck_generated", { theme });
      router.push(`/${handle}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex w-full max-w-md flex-col items-center gap-6 py-6">
        <div className="relative h-24 w-20">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute inset-0 rounded-xl border-2 border-[var(--ink)] bg-[var(--surface)]"
              animate={{ rotate: [(i - 1) * 8, (i - 1) * 8 + 4, (i - 1) * 8], y: [0, -4, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.15 }}
              style={{ zIndex: 3 - i }}
            />
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="text-sm font-medium text-[var(--ink)]"
          >
            {STEPS[step]}
          </motion.p>
        </AnimatePresence>
        <div className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-[var(--ink)]/10">
          <motion.div
            className="h-full rounded-full bg-[var(--accent)]"
            initial={{ width: "8%" }}
            animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            transition={{ ease: "easeOut" }}
          />
        </div>
      </div>
    );
  }

  return (
    <motion.form
      onSubmit={submit}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25 }}
      className="flex w-full max-w-md flex-col gap-3"
    >
      <div className="flex overflow-hidden rounded-2xl border border-[var(--ink)]/15 bg-[var(--surface)] transition focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-[var(--accent)]/30">
        <span className="flex items-center pl-4 font-mono text-sm text-[var(--muted)]">
          github.com/
        </span>
        <input
          value={username}
          onChange={(e) => onUsernameChange(e.target.value)}
          placeholder="your-username"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          className="flex-1 bg-transparent px-2 py-4 text-lg text-[var(--ink)] outline-none placeholder:text-[var(--muted)]/60"
        />
      </div>

      <button
        type="submit"
        className="rounded-2xl bg-[var(--accent)] py-4 font-display text-lg font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-[0.98]"
      >
        Roll my reel →
      </button>

      {error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="flex items-start gap-2 rounded-xl border border-red-300 bg-red-50 px-3 py-2.5 text-sm text-red-700"
        >
          <span>⚠️</span>
          <span>{error}</span>
        </motion.div>
      )}
    </motion.form>
  );
}
