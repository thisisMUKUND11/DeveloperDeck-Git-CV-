"use client";

import {
  AnimatePresence,
  motion,
  useMotionValue,
  useTransform,
  type PanInfo,
} from "framer-motion";
import { useEffect, useState } from "react";

import type { Card } from "@/lib/api";
import type { Theme } from "@/lib/themes";
import { ProofCard } from "./ProofCard";

const SWIPE_THRESHOLD = 80;
const FLING_VELOCITY = 450;

/** The front, draggable card. Its own motion value drives the live tilt — kept
 *  separate from the enter/exit animation so the two never fight. Vertical
 *  scrolling inside the card is preserved via dragDirectionLock. */
function DraggableCard({
  card,
  theme,
  canPrev,
  canNext,
  onCommit,
}: {
  card: Card;
  theme: Theme;
  canPrev: boolean;
  canNext: boolean;
  onCommit: (dir: 1 | -1) => void;
}) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-220, 0, 220], [-9, 0, 9]);
  const nextHint = useTransform(x, [-150, -30], [1, 0]);
  const prevHint = useTransform(x, [30, 150], [0, 1]);

  const onDragEnd = (_: unknown, info: PanInfo) => {
    const dx = info.offset.x;
    const vx = info.velocity.x;
    if (canNext && (dx < -SWIPE_THRESHOLD || vx < -FLING_VELOCITY)) onCommit(1);
    else if (canPrev && (dx > SWIPE_THRESHOLD || vx > FLING_VELOCITY)) onCommit(-1);
    // Otherwise dragConstraints snaps it back to centre automatically.
  };

  return (
    <motion.div
      className="absolute inset-0 cursor-grab touch-pan-y active:cursor-grabbing"
      style={{ x, rotate }}
      drag="x"
      dragDirectionLock
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.55}
      onDragEnd={onDragEnd}
      whileDrag={{ scale: 1.02 }}
    >
      <ProofCard card={card} theme={theme} />
      {canNext && (
        <motion.div
          style={{ opacity: nextHint }}
          className="pointer-events-none absolute right-4 top-4 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-bold text-white"
        >
          NEXT →
        </motion.div>
      )}
      {canPrev && (
        <motion.div
          style={{ opacity: prevHint }}
          className="pointer-events-none absolute left-4 top-4 rounded-full bg-[var(--ink)] px-3 py-1 text-xs font-bold text-[var(--bg)]"
        >
          ← BACK
        </motion.div>
      )}
    </motion.div>
  );
}

function ArrowButton({
  dir,
  disabled,
  onClick,
}: {
  dir: -1 | 1;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={dir === 1 ? "Next card" : "Previous card"}
      className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[var(--ink)]/20 bg-[var(--surface)] text-lg text-[var(--ink)] shadow-sm transition hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-25 sm:flex"
    >
      {dir === 1 ? "→" : "←"}
    </button>
  );
}

export function CardStack({ cards, theme }: { cards: Card[]; theme: Theme }) {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(0);

  const go = (delta: 1 | -1) => {
    const target = index + delta;
    if (target < 0 || target > cards.length - 1) return;
    setDir(delta);
    setIndex(target);
  };

  // Keyboard navigation — clearly intuitive on desktop.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const atEnd = index >= cards.length - 1;
  const atStart = index <= 0;
  const showDots = cards.length <= 12;

  return (
    <div className="flex w-full flex-col items-center gap-5">
      <div className="flex w-full items-center justify-center gap-2 sm:gap-4">
        <ArrowButton dir={-1} disabled={atStart} onClick={() => go(-1)} />

        <div className="relative h-[66vh] max-h-[520px] min-h-[400px] w-full max-w-[360px]">
          {/* Layered depth behind the active card. */}
          {cards[index + 1] && (
            <div className="pointer-events-none absolute inset-0 translate-y-3 scale-[0.955] opacity-50">
              <ProofCard card={cards[index + 1]} theme={theme} />
            </div>
          )}

          <AnimatePresence custom={dir} initial={false} mode="popLayout">
            <motion.div
              key={index}
              className="absolute inset-0"
              custom={dir}
              initial={{ x: dir >= 0 ? 280 : -280, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: dir >= 0 ? -280 : 280, opacity: 0 }}
              transition={{ type: "spring", stiffness: 420, damping: 36 }}
            >
              <DraggableCard
                card={cards[index]}
                theme={theme}
                canPrev={!atStart}
                canNext={!atEnd}
                onCommit={go}
              />
            </motion.div>
          </AnimatePresence>
        </div>

        <ArrowButton dir={1} disabled={atEnd} onClick={() => go(1)} />
      </div>

      {showDots && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {cards.map((_, i) => (
            <button
              key={i}
              aria-label={`Go to card ${i + 1}`}
              onClick={() => {
                setDir(i > index ? 1 : -1);
                setIndex(i);
              }}
              className="h-2 rounded-full transition-all"
              style={{
                width: i === index ? 22 : 8,
                background: i === index ? "var(--accent)" : "var(--muted)",
                opacity: i === index ? 1 : 0.4,
              }}
            />
          ))}
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
        <span className="font-mono">
          {index + 1} / {cards.length}
        </span>
        <span className="hidden sm:inline">· swipe, use ← → keys, or the arrows</span>
        <span className="sm:hidden">· swipe to explore</span>
      </div>
    </div>
  );
}
