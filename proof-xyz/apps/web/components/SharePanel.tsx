"use client";

import { AnimatePresence, motion } from "framer-motion";
import QRCode from "qrcode";
import { useMemo, useState } from "react";

import { createShare, getShareStats, type Card } from "@/lib/api";
import { BRAND_SLUG } from "@/lib/brand";

function shareBase() {
  const env = process.env.NEXT_PUBLIC_PUBLIC_BASE_URL;
  if (env) return env;
  return typeof window !== "undefined" ? window.location.origin : "";
}

export function SharePanel({
  username,
  cards,
  theme,
}: {
  username: string;
  cards: Card[];
  theme: string;
}) {
  const shareable = useMemo(() => cards.filter((c) => !c.locked), [cards]);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(shareable.map((c) => c.repo)),
  );
  const [link, setLink] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [showQr, setShowQr] = useState(false);
  const [views, setViews] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setLink(null);
    setToken(null);
    setQr(null);
    setShowQr(false);
    setViews(null);
    setCopied(false);
  };

  const toggle = (repo: string) => {
    reset();
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(repo) ? next.delete(repo) : next.add(repo);
      return next;
    });
  };

  const allOn = selected.size === shareable.length;
  const setAll = (on: boolean) => {
    reset();
    setSelected(on ? new Set(shareable.map((c) => c.repo)) : new Set());
  };

  const copyLink = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const tok = await createShare(username, [...selected], theme);
      const url = `${shareBase()}/s/${tok}`;
      setToken(tok);
      setLink(url);
      setViews(0);
      QRCode.toDataURL(url, { width: 240, margin: 1 }).then(setQr).catch(() => {});
      try {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2200);
      } catch {
        /* clipboard blocked — link shown below for manual copy */
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create link");
    } finally {
      setBusy(false);
    }
  };

  const refreshViews = async () => {
    if (token) setViews(await getShareStats(token));
  };

  return (
    <div className="w-full max-w-md">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--accent)] px-5 py-3.5 font-display font-semibold text-white shadow-lg shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-[0.98]"
      >
        🔗 Get a shareable link
        <span className={`transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 flex flex-col gap-3 rounded-2xl border border-[var(--ink)]/12 bg-[var(--surface)] p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-[var(--ink)]">
                  Pick what recruiters will see
                </p>
                <button
                  onClick={() => setAll(!allOn)}
                  className="shrink-0 text-xs font-semibold text-[var(--accent)]"
                >
                  {allOn ? "Clear all" : "Select all"}
                </button>
              </div>

              <div className="proof-scroll flex max-h-[min(60vh,30rem)] flex-col gap-1.5 overflow-y-auto pr-1">
                {shareable.map((c) => {
                  const on = selected.has(c.repo);
                  return (
                    <button
                      key={c.repo}
                      onClick={() => toggle(c.repo)}
                      className={`flex items-center gap-3 rounded-xl border px-3 py-2 text-left transition ${
                        on
                          ? "border-[var(--accent)]/60 bg-[var(--accent)]/10"
                          : "border-[var(--ink)]/10 opacity-55"
                      }`}
                    >
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                          on
                            ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                            : "border-[var(--muted)]"
                        }`}
                      >
                        {on && <span className="text-[10px] leading-none">✓</span>}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-mono text-sm text-[var(--ink)]">
                          {c.repo}
                        </span>
                        {c.summary && (
                          <span className="block truncate text-xs text-[var(--muted)]">
                            {c.summary}
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={copyLink}
                disabled={busy || selected.size === 0}
                className="rounded-xl bg-[var(--accent)] py-3 font-display text-sm font-semibold text-white shadow-md shadow-[var(--accent)]/25 transition hover:brightness-105 active:scale-[0.98] disabled:opacity-40"
              >
                {busy
                  ? "Creating link…"
                  : copied
                    ? "✓ Copied to clipboard"
                    : `Copy link · ${selected.size} project${selected.size === 1 ? "" : "s"}`}
              </button>

              {error && <p className="text-xs text-red-600">{error}</p>}

              {link && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col gap-2"
                >
                  <div className="flex items-center overflow-hidden rounded-xl border border-[var(--ink)]/15 bg-[var(--bg)] px-3 py-2.5">
                    <span className="truncate font-mono text-xs text-[var(--ink)]">
                      {link.replace(/^https?:\/\//, "")}
                    </span>
                  </div>

                  {/* analytics + QR controls */}
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <button
                      onClick={refreshViews}
                      className="flex items-center gap-1.5 text-[var(--muted)] transition hover:text-[var(--ink)]"
                    >
                      👁 Opened {views ?? 0} {views === 1 ? "time" : "times"}
                      <span className="text-[var(--accent)]">↻</span>
                    </button>
                    <button
                      onClick={() => setShowQr((s) => !s)}
                      className="font-semibold text-[var(--accent)]"
                    >
                      {showQr ? "Hide QR" : "Show QR"}
                    </button>
                  </div>

                  {showQr && qr && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center gap-2 rounded-xl bg-white p-3"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={qr} alt="QR code for your link" className="h-40 w-40" />
                      <a
                        href={qr}
                        download={`${username}-${BRAND_SLUG}-qr.png`}
                        className="text-xs font-semibold text-[var(--accent)]"
                      >
                        Download QR ↓
                      </a>
                    </motion.div>
                  )}

                  <p className="text-[11px] text-[var(--muted)]">
                    Paste it on your résumé. Each link is unique and only reveals the
                    selected projects — change the picks and copy again for a new one.
                  </p>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
