// Motion presets. Calm: short, ease-out, small distances, no bounce. Every animated thing
// in Zyn uses one of these so the whole app moves the same way.
import type { Transition, Variants } from "motion/react";

export const EASE = [0.2, 0, 0, 1] as const;
export const T_FAST: Transition = { duration: 0.15, ease: EASE };
export const T_BASE: Transition = { duration: 0.24, ease: EASE };
export const T_LAYOUT: Transition = { type: "spring", stiffness: 420, damping: 40, mass: 0.8 };

/** Page and tab content arriving. */
export const enter: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: T_BASE },
  exit: { opacity: 0, y: -4, transition: { duration: 0.12, ease: EASE } },
};

/** Frequent switches (tabs, runs, the palette): opacity only, quick, no exit wait. */
export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: T_FAST },
  exit: { opacity: 0, transition: { duration: 0.08 } },
};

/** Items in a list: same as enter, staggered for the first screenful only. */
export const item = (i: number): Variants => ({
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { ...T_BASE, delay: Math.min(i % 40, 10) * 0.03 } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: 0.12, ease: EASE } },
});

/** Small things swapping in place (status badge, counts label). */
export const swap: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  show: { opacity: 1, scale: 1, transition: T_FAST },
  exit: { opacity: 0, scale: 0.92, transition: { duration: 0.1 } },
};

/** AutoAnimate settings for small lists that rearrange in place (check chips). */
export const AUTO = { duration: 180, easing: "ease-out" } as const;
