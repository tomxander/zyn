import { type CSSProperties, useEffect, useRef, useState } from "react";
import { reduced, useRunWhileVisible, useVisible } from "./runtime";

/**
 * A two-row checker band across the full width. On mount the cells appear from the centre
 * outward, with a little jitter, over about 0.72 s. Hard-edged squares, no fades.
 */
export function CheckerBand({ variant = "checker" }: { variant?: "checker" | "solid" }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext("2d")!;
    let cells: [number, number][] = [];
    let shown = 0;
    let raf = 0;
    let cell = 20;
    const color = () => getComputedStyle(c).color;
    const layout = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = c.clientWidth;
      const h = c.clientHeight;
      c.width = Math.round(w * dpr);
      c.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cell = h / 2;
      const cols = Math.ceil(w / cell);
      const mid = cols / 2;
      const list: { c: number; r: number; k: number }[] = [];
      for (let col = 0; col < cols; col++)
        for (let r = 0; r < 2; r++) {
          if (variant === "checker" && (col + r) % 2 === 0) continue;
          list.push({ c: col, r, k: Math.abs(col - mid) + 8 * Math.random() });
        }
      list.sort((a, b) => a.k - b.k);
      const frac = cells.length ? shown / cells.length : 0;
      cells = list.map((x) => [x.c, x.r]);
      shown = Math.round(frac * cells.length);
      paint();
    };
    const paint = () => {
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.fillStyle = color();
      for (let i = 0; i < shown; i++) ctx.fillRect(Math.floor(cells[i][0] * cell), Math.floor(cells[i][1] * cell), Math.ceil(cell), Math.ceil(cell));
    };
    layout();
    if (reduced()) {
      shown = cells.length;
      paint();
    } else {
      let lastT = performance.now();
      let carry = 0;
      const step = (now: number) => {
        const dt = Math.min(32, now - lastT);
        lastT = now;
        carry += dt;
        const every = (720 / cells.length) * (0.65 + 0.7 * Math.random());
        while (carry >= every && shown < cells.length) {
          carry -= every;
          shown++;
        }
        paint();
        if (shown < cells.length) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }
    const ro = new ResizeObserver(layout);
    ro.observe(c);
    const mo = new MutationObserver(paint); // theme change recolours
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      mo.disconnect();
    };
  }, [variant]);
  return (
    <div className="band" aria-hidden>
      <canvas ref={ref} />
    </div>
  );
}

/**
 * A 1 px rule the width of the content column, with ink blocks sliding along it at 200 px/s.
 * It is pre-warmed: it starts mid-stream, never empty. Paused off screen.
 */
export function SliderRule({ widths = [32, 40], gap = 0.49 }: { widths?: number[]; gap?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [rects, setRects] = useState<{ id: number; w: number; delay: number; dur: number }[]>([]);
  const st = useRef({ seq: 0, next: 0, width: 0, wi: 0 });
  useVisible(ref);

  const spawnSpec = (W: number) => {
    const s = st.current;
    const w = widths[s.wi++ % widths.length];
    return { w, dur: (W + w) / 200, interval: (gap * W * (0.85 + 0.3 * Math.random()) + w) / 200 };
  };

  useEffect(() => {
    const el = ref.current!;
    const W = el.clientWidth;
    st.current.width = W;
    if (reduced()) return;
    // back-fill the past so the rule looks mid-stream
    const pre: { id: number; w: number; delay: number; dur: number }[] = [];
    let t = 0;
    for (;;) {
      const s = spawnSpec(W);
      if (t > s.dur) break;
      pre.push({ id: ++st.current.seq, w: s.w, delay: -t, dur: s.dur });
      t += s.interval;
    }
    setRects(pre.slice(0, 4));
    st.current.next = spawnSpec(W).interval * 0.5;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useRunWhileVisible(ref, (dt) => {
    const s = st.current;
    s.next -= dt;
    if (s.next > 0) return;
    const spec = spawnSpec(ref.current!.clientWidth);
    s.next = spec.interval;
    setRects((r) => [...r.slice(-3), { id: ++s.seq, w: spec.w, delay: 0, dur: spec.dur }]);
  });

  return (
    <div className="slider" ref={ref} data-run-surface aria-hidden>
      {rects.map((r) => (
        <i
          key={r.id}
          style={{ width: r.w, animationDuration: `${r.dur}s`, animationDelay: `${r.delay}s` } as CSSProperties}
        />
      ))}
    </div>
  );
}
