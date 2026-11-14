import { type CSSProperties, useEffect, useRef, useState } from "react";
import { reduced, useRunWhileVisible } from "./runtime";

/* The footer wordmark, with a square lens. Inside the lens the mark shows its alternate:
   outlined letters on the accent field, the Z route closed. The lens follows the pointer;
   when the pointer leaves, the square is launched with the pointer's speed and bounces
   forever inside the band between the two rules. Every exit adds one more (at most 6). */

function Mark({ alt = false }: { alt?: boolean }) {
  return (
    <svg viewBox="0 0 60 24" className="wm__svg" preserveAspectRatio="xMidYMid meet">
      <path
        d="M3 3 L21 3 L3 21 L21 21"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
        strokeDasharray={alt ? undefined : "26.97792206 7.5 1000 1000"}
      />
      <rect x="20" y="20" width="2" height="2" fill={alt ? "currentColor" : "var(--accent)"} />
      <g transform="translate(30 18)" fill={alt ? "none" : "currentColor"} stroke={alt ? "currentColor" : "none"} strokeWidth={alt ? 18 : 0}>
        <path d="M340 111V0H21V111L215 579H31V690H336V579L143 111Z" transform="scale(0.02 -0.02)" />
        <path d="M269 269V0H146V271L6 690H141L207 426L273 690H409Z" transform="translate(8.38 0) scale(0.02 -0.02)" />
        <path d="M432 690V0H309L165 368V0H42V690H165L309 306V690Z" transform="translate(17.88 0) scale(0.02 -0.02)" />
      </g>
    </svg>
  );
}

type Sq = { id: number; x: number; y: number; vx: number; vy: number };
let seq = 0;

export function Wordmark() {
  const box = useRef<HTMLDivElement>(null);
  const [lens, setLens] = useState<{ x: number; y: number } | null>(null);
  const [squares, setSquares] = useState<Sq[]>([]);
  const size = useRef(120);
  const last = useRef<{ x: number; y: number; t: number; vx: number; vy: number } | null>(null);
  const sqs = useRef<Sq[]>([]);
  const fine = typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  useEffect(() => {
    const el = box.current!;
    const fit = () => (size.current = Math.round(el.clientHeight * 0.42));
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const clamp = (x: number, y: number) => {
    const el = box.current!;
    const h = size.current / 2;
    return { x: Math.min(el.clientWidth - h, Math.max(h, x)), y: Math.min(el.clientHeight - h, Math.max(h, y)) };
  };

  const onMove = (e: React.PointerEvent) => {
    if (!fine || reduced()) return;
    const r = box.current!.getBoundingClientRect();
    const p = clamp(e.clientX - r.left, e.clientY - r.top);
    const now = performance.now();
    if (last.current) {
      const dt = Math.max(1, now - last.current.t);
      last.current = { ...p, t: now, vx: (p.x - last.current.x) / dt, vy: (p.y - last.current.y) / dt };
    } else last.current = { ...p, t: now, vx: 0, vy: 0 };
    setLens(p);
  };

  const onLeave = () => {
    const l = last.current;
    setLens(null);
    last.current = null;
    if (!l || !fine || reduced()) return;
    const el = box.current!;
    const diag = Math.hypot(el.clientWidth, el.clientHeight);
    const ps = Math.hypot(l.vx, l.vy); // px per ms
    const speed = Math.min(800, Math.max(280, 0.19 * diag + 240 * ps));
    let ax = ps > 0.01 ? l.vx / ps : Math.random() - 0.5;
    let ay = ps > 0.01 ? l.vy / ps : Math.random() - 0.5;
    const n = Math.hypot(ax, ay) || 1;
    ax /= n;
    ay /= n;
    // never slide flat: each axis keeps at least 18% of the speed
    if (Math.abs(ax) < 0.18) ax = 0.18 * Math.sign(ax || 1);
    if (Math.abs(ay) < 0.18) ay = 0.18 * Math.sign(ay || 1);
    const sq: Sq = { id: ++seq, x: l.x, y: l.y, vx: ax * speed, vy: ay * speed };
    sqs.current = [...sqs.current.slice(-5), sq];
    setSquares(sqs.current.map((s) => ({ ...s })));
  };

  useRunWhileVisible(
    box,
    (dt) => {
      if (!sqs.current.length) return;
      const el = box.current!;
      const h = size.current / 2;
      const W = el.clientWidth,
        H = el.clientHeight;
      const step = Math.min(dt, 0.032);
      for (const s of sqs.current) {
        s.x += s.vx * step;
        s.y += s.vy * step;
        if (s.x < h) ((s.x = h), (s.vx = Math.abs(s.vx)));
        if (s.x > W - h) ((s.x = W - h), (s.vx = -Math.abs(s.vx)));
        if (s.y < h) ((s.y = h), (s.vy = Math.abs(s.vy)));
        if (s.y > H - h) ((s.y = H - h), (s.vy = -Math.abs(s.vy)));
      }
      setSquares(sqs.current.map((s) => ({ ...s })));
    },
    true,
  );

  const lenses = [...squares, ...(lens ? [{ id: 0, ...lens }] : [])];
  return (
    <div className="wm" ref={box} onPointerMove={onMove} onPointerLeave={onLeave} aria-hidden>
      <Mark />
      {lenses.map((l) => {
        const h = size.current / 2;
        const style = {
          clipPath: `inset(${l.y - h}px calc(100% - ${l.x + h}px) calc(100% - ${l.y + h}px) ${l.x - h}px)`,
        } as CSSProperties;
        return (
          <div key={l.id} className="wm__lens" style={style}>
            <Mark alt />
            <span className="wm__edge" style={{ left: l.x - h, top: l.y - h, width: h * 2, height: h * 2 }} />
          </div>
        );
      })}
    </div>
  );
}
