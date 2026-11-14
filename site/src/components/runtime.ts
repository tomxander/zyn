import { type RefObject, useEffect, useRef, useState } from "react";

/* The motion runtime every animation on the page shares.
   - One IntersectionObserver decides what is on screen (and the tab must be visible).
   - One requestAnimationFrame loop ticks only the subscribers that are visible.
   - Time is visible time: scroll away and a timeline freezes; come back and it resumes.
   CSS loops pause the same way: an element with [data-run-surface] gets [data-visible]
   only while it is on screen, and a global rule pauses animations inside it otherwise. */

export const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

type Watcher = (v: boolean) => void;
const watchers = new Map<Element, Set<Watcher>>();
const state = new Map<Element, boolean>();
let io: IntersectionObserver | null = null;

function observer() {
  if (io) return io;
  io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      state.set(e.target, e.isIntersecting);
      const v = e.isIntersecting && document.visibilityState === "visible";
      watchers.get(e.target)?.forEach((w) => w(v));
    }
  });
  document.addEventListener("visibilitychange", () => {
    for (const [el, set] of watchers) {
      const v = !!state.get(el) && document.visibilityState === "visible";
      set.forEach((w) => w(v));
    }
  });
  return io;
}

export function watchVisible(el: Element, fn: Watcher) {
  const obs = observer();
  let set = watchers.get(el);
  if (!set) {
    set = new Set();
    watchers.set(el, set);
    obs.observe(el);
  }
  set.add(fn);
  if (state.has(el)) fn(!!state.get(el) && document.visibilityState === "visible");
  return () => {
    set!.delete(fn);
    if (!set!.size) {
      watchers.delete(el);
      obs.unobserve(el);
    }
  };
}

/* one shared frame loop */
type Tick = (dt: number) => void;
const ticks = new Set<Tick>();
let raf = 0;
let last = 0;
function loop(now: number) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (import.meta.env.DEV) {
    // dev only: how long our own per-frame work takes (window.__zynPerf)
    const a = performance.now();
    ticks.forEach((t) => t(dt));
    const p = ((window as unknown as { __zynPerf?: { n: number; total: number; worst: number } }).__zynPerf ??= { n: 0, total: 0, worst: 0 });
    const d = performance.now() - a;
    p.n++;
    p.total += d;
    p.worst = Math.max(p.worst, d);
  } else ticks.forEach((t) => t(dt));
  raf = ticks.size ? requestAnimationFrame(loop) : 0;
}
function addTick(t: Tick) {
  ticks.add(t);
  if (!raf) {
    last = performance.now();
    raf = requestAnimationFrame(loop);
  }
  return () => ticks.delete(t);
}

/** Calls tick(dt) every frame, but only while `ref` is on screen. dt is clamped to 0.1 s. */
export function useRunWhileVisible(ref: RefObject<Element | null>, tick: Tick, enabled = true) {
  const fn = useRef(tick);
  fn.current = tick;
  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled || reduced()) return;
    let stop: (() => void) | null = null;
    const off = watchVisible(el, (v) => {
      if (v && !stop) stop = addTick((dt) => fn.current(dt));
      if (!v && stop) {
        stop();
        stop = null;
      }
    });
    return () => {
      off();
      stop?.();
    };
  }, [ref, enabled]);
}

/** True while the element is on screen; also marks it [data-visible] so CSS loops inside run. */
export function useVisible(ref: RefObject<Element | null>) {
  const [v, setV] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    return watchVisible(el, (on) => {
      setV(on);
      if (on) el.setAttribute("data-visible", "");
      else el.removeAttribute("data-visible");
    });
  }, [ref]);
  return v;
}

/** Seconds of visible time since the element was first seen (re-renders ~each frame while running). */
export function useVisibleClock(ref: RefObject<Element | null>, until = Infinity) {
  const [t, setT] = useState(0);
  const acc = useRef(0);
  useRunWhileVisible(
    ref,
    (dt) => {
      if (acc.current >= until) return;
      acc.current += dt;
      setT(acc.current);
    },
    true,
  );
  return reduced() ? until : t;
}

export const HOUSE = [0.6, 0.6, 0, 1] as const;
export const QUART = [0.165, 0.84, 0.44, 1] as const;
export const SHARP = [0.9, 0, 0.1, 1] as const;

export const hash = (e: number, t: number) => {
  const x = Math.sin((e + 1) * 12.9898 + (t + 1) * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

/** cubic-bezier easing as a function, for canvas work. */
export function bezier(p1x: number, p1y: number, p2x: number, p2y: number) {
  const cx = 3 * p1x,
    bx = 3 * (p2x - p1x) - cx,
    ax = 1 - cx - bx;
  const cy = 3 * p1y,
    by = 3 * (p2y - p1y) - cy,
    ay = 1 - cy - by;
  const sx = (t: number) => ((ax * t + bx) * t + cx) * t;
  const sy = (t: number) => ((ay * t + by) * t + cy) * t;
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx;
  return (x: number) => {
    let t = x;
    for (let i = 0; i < 6; i++) {
      const d = dx(t);
      if (Math.abs(d) < 1e-6) break;
      t -= (sx(t) - x) / d;
    }
    return sy(Math.min(1, Math.max(0, t)));
  };
}
export const easeHouse = bezier(0.6, 0.6, 0, 1);
