"use client";

import {
  AnimatePresence,
  motion,
  useMotionValue,
  useTransform,
  type PanInfo,
} from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";

// Kept intentionally low so a short, gentle swipe still registers on phones.
const SWIPE_THRESHOLD = 55;
const FLING_VELOCITY = 300;

// The deck, its progress bar and its buttons must share one width. It grows on
// tablets: the desktop grid only takes over at lg, so without this an iPad in
// portrait (768px) showed a 340px card marooned in empty space.
const DECK_WIDTH = "w-full max-w-[340px] sm:max-w-[390px] md:max-w-[460px]";

// Above this many slides the progress bar stops being a row of tappable
// segments. At 16 slides in a 340px bar each segment is ~15px — well under the
// ~44px touch target guideline, so tapping an exact one isn't realistic.
const MAX_TAPPABLE_SEGMENTS = 10;

/** The front, draggable slide. Its motion value drives the live tilt — kept
 *  separate from the enter/exit animation so the two never fight. Vertical
 *  scrolling inside the card is preserved via dragDirectionLock. */
function DraggableSlide({
  children,
  canPrev,
  canNext,
  onCommit,
}: {
  children: ReactNode;
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
      {children}
      {/* Hints sit at the vertical centre of the card edges so they never
          overlap the header (repo name / stat badge). */}
      {canNext && (
        <motion.div
          style={{ opacity: nextHint }}
          className="pointer-events-none absolute right-3 top-1/2 z-10 -translate-y-1/2 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-bold text-white shadow-lg"
        >
          NEXT →
        </motion.div>
      )}
      {canPrev && (
        <motion.div
          style={{ opacity: prevHint }}
          className="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 rounded-full bg-[var(--ink)] px-3 py-1 text-xs font-bold text-[var(--bg)] shadow-lg"
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
      aria-label={dir === 1 ? "Next" : "Previous"}
      className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--ink)]/20 bg-[var(--surface)] text-lg text-[var(--ink)] shadow-sm transition hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-25 sm:flex"
    >
      {dir === 1 ? "→" : "←"}
    </button>
  );
}

export function CardStack({ slides }: { slides: ReactNode[] }) {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(0);

  const go = (delta: 1 | -1) => {
    const target = index + delta;
    if (target < 0 || target > slides.length - 1) return;
    setDir(delta);
    setIndex(target);
  };

  // Depends on what `go` actually reads, so the listener is re-bound only when
  // the position changes rather than on every render.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Don't steal the arrow keys from a focused text field.
      const el = e.target as HTMLElement | null;
      if (el?.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el?.tagName ?? "")) {
        return;
      }
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, slides.length]);

  const atEnd = index >= slides.length - 1;
  const atStart = index <= 0;
  const segmented = slides.length <= MAX_TAPPABLE_SEGMENTS;

  const jumpTo = (i: number) => {
    if (i === index) return;
    setDir(i > index ? 1 : -1);
    setIndex(i);
  };

  return (
    <div className="flex w-full flex-col items-center gap-5">
      {/* Story-style progress bar. With few slides each segment is tappable to
          jump; past MAX_TAPPABLE_SEGMENTS they'd be too narrow to hit, so it
          becomes one continuous track and navigation falls to swipe/buttons. */}
      {segmented ? (
        <div className={`flex ${DECK_WIDTH} gap-1.5`}>
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => jumpTo(i)}
              aria-label={`Go to slide ${i + 1}`}
              className="group flex-1 py-1.5"
            >
              <span className="block h-1 overflow-hidden rounded-full bg-[var(--ink)]/12">
                <motion.span
                  className="block h-full rounded-full bg-[var(--accent)]"
                  initial={false}
                  animate={{ width: i <= index ? "100%" : "0%" }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                />
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div
          className={`${DECK_WIDTH} py-1.5`}
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={slides.length}
          aria-valuenow={index + 1}
          aria-label={`Slide ${index + 1} of ${slides.length}`}
        >
          <span className="block h-1 overflow-hidden rounded-full bg-[var(--ink)]/12">
            <motion.span
              className="block h-full rounded-full bg-[var(--accent)]"
              initial={false}
              animate={{ width: `${((index + 1) / slides.length) * 100}%` }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            />
          </span>
        </div>
      )}

      <div className="flex w-full items-center justify-center gap-2 sm:gap-3">
        <ArrowButton dir={-1} disabled={atStart} onClick={() => go(-1)} />

        {/* dvh, not vh: on mobile browsers vh is the *largest* viewport height
            and ignores the address bar, so the card overflowed the visible area
            until the toolbar collapsed. Matches the 100dvh used on .proof-root.
            The min-height relaxes on short viewports (landscape phones) where a
            400px floor pushed the Back/Next buttons off screen. */}
        <div
          className={`relative h-[66dvh] max-h-[520px] min-h-[340px] md:max-h-[620px] [@media(min-height:700px)]:min-h-[400px] ${DECK_WIDTH}`}
        >
          {/* Two peeked cards behind the top one give the stack real depth. */}
          {slides[index + 2] && (
            <div className="pointer-events-none absolute inset-0 translate-y-6 scale-[0.9] opacity-25">
              {slides[index + 2]}
            </div>
          )}
          {slides[index + 1] && (
            <div className="pointer-events-none absolute inset-0 translate-y-3 scale-[0.955] opacity-50">
              {slides[index + 1]}
            </div>
          )}

          <AnimatePresence custom={dir} initial={false} mode="popLayout">
            <motion.div
              key={index}
              className="absolute inset-0"
              custom={dir}
              initial={{ x: dir >= 0 ? 280 : -280, opacity: 0, rotate: dir >= 0 ? 4 : -4 }}
              animate={{ x: 0, opacity: 1, rotate: 0 }}
              exit={{ x: dir >= 0 ? -280 : 280, opacity: 0, rotate: dir >= 0 ? -4 : 4 }}
              transition={{ type: "spring", stiffness: 420, damping: 36 }}
            >
              <DraggableSlide canPrev={!atStart} canNext={!atEnd} onCommit={go}>
                {slides[index]}
              </DraggableSlide>
            </motion.div>
          </AnimatePresence>
        </div>

        <ArrowButton dir={1} disabled={atEnd} onClick={() => go(1)} />
      </div>

      {/* Mobile: explicit Back / Next buttons so navigation never depends on
          the swipe gesture (the side arrows are hidden below the sm breakpoint). */}
      <div className={`flex items-center gap-3 sm:hidden ${DECK_WIDTH}`}>
        <button
          onClick={() => go(-1)}
          disabled={atStart}
          className="flex-1 rounded-xl border border-[var(--ink)]/20 bg-[var(--surface)] py-3 font-display text-sm font-semibold text-[var(--ink)] transition active:scale-95 disabled:opacity-30"
        >
          ← Back
        </button>
        <button
          onClick={() => go(1)}
          disabled={atEnd}
          className="flex-1 rounded-xl bg-[var(--accent)] py-3 font-display text-sm font-semibold text-white shadow-md shadow-[var(--accent)]/25 transition active:scale-95 disabled:opacity-30"
        >
          Next →
        </button>
      </div>

      <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
        <span className="font-mono">
          {index + 1} / {slides.length}
        </span>
        <span className="hidden sm:inline">· swipe, use ← → keys, or the arrows</span>
        <span className="sm:hidden">· tap Next, the bar, or swipe</span>
      </div>
    </div>
  );
}
