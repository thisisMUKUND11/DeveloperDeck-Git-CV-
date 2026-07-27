"use client";

import { MotionConfig } from "framer-motion";

/** Makes Framer Motion honour the OS "reduce motion" setting.
 *
 * The `prefers-reduced-motion` block in globals.css only zeroes CSS animation
 * and transition durations. Framer Motion animates by writing inline transforms
 * from JS, so none of it is covered — the card-swipe springs, the drag tilt and
 * the rotating headline would all still run at full strength. Its own default
 * is `reducedMotion: "never"`, so this has to be opted into explicitly.
 *
 * "user" keeps opacity fades (which don't trigger motion sickness) and disables
 * transform-based movement when the OS asks for it.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
