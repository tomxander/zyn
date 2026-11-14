import { useEffect, useRef } from "react";
import { easeHouse, hash, reduced, useRunWhileVisible } from "./runtime";

/* Line art behind a panel, drawn on a canvas, with ink "traffic" running along the lines in the
   outer border band only (so the content card in the middle stays calm):
   - bold: a 2 px ink stroke sliding along a 1 px line
   - gap: a short erased stretch travelling the line, with one or two smaller gaps behind it
   Speeds 360 to 1100 px/s, linear. A pattern change morphs the art over 0.8 s: old lines retract
   toward the centre, new lines grow outward. Paused off screen; still under reduced motion. */

export type Pattern = "fisheye" | "waves" | "arcs" | "fan" | "lattice" | "tunnel" | "mesh" | "bow";

type Pt = [number, number];
type Path = { pts: Pt[]; cum: number[]; len: number; windows: [number, number][]; key: number };
type Event = { path: number; win: [number, number]; kind: "bold" | "gap"; len: number; speed: number; t: number; tails: { off: number; w: number }[] };

const N = 40;
function lines(p: Pattern): Pt[][] {
  const out: Pt[][] = [];
  const seg = (f: (t: number) => Pt, n = N) => out.push(Array.from({ length: n + 1 }, (_, i) => f(i / n)));
  switch (p) {
    case "fisheye": {
      // a barrel-distorted grid: lines crowd toward the rim
      const warp = (u: number, v: number): Pt => {
        const r2 = u * u + v * v;
        const k = 1 + 0.42 * r2;
        return [0.5 + (0.5 * u * k) / 1.42, 0.5 + (0.5 * v * k) / 1.42];
      };
      for (let i = -9; i <= 9; i++) {
        const c = i / 9;
        seg((t) => warp(c, t * 2 - 1));
        seg((t) => warp(t * 2 - 1, c));
      }
      break;
    }
    case "waves":
      for (let i = -2; i <= 22; i++) seg((t) => [i / 20 + 0.035 * Math.sin(t * Math.PI * 3 + i * 0.6), t], 60);
      break;
    case "arcs":
      for (let i = 1; i <= 18; i++) {
        const r = i * 0.085;
        seg((t) => [r * Math.cos((t * Math.PI) / 2), 1 - r * Math.sin((t * Math.PI) / 2)], 50);
      }
      break;
    case "fan":
      for (let i = 0; i <= 26; i++) {
        const a = Math.PI + (i / 26) * Math.PI;
        seg((t) => [0.5 + Math.cos(a) * t * 1.2, 1 + Math.sin(a) * t * 1.2]);
      }
      break;
    case "lattice":
      for (let i = -10; i <= 10; i++) {
        seg((t) => [t, i / 10 + t * 0.6]);
        seg((t) => [t, i / 10 + 0.6 - t * 0.6]);
      }
      for (let i = 1; i < 5; i++) seg((t) => [t, i / 5]);
      break;
    case "mesh":
      for (let i = 1; i < 14; i++) {
        seg((t) => [i / 14, t]);
        seg((t) => [t, i / 14]);
      }
      break;
    case "bow":
      for (let i = 0; i <= 18; i++) {
        const y = i / 18;
        seg((t) => [t, y + 0.16 * (y - 0.5) * Math.sin(t * Math.PI) * 2]);
      }
      break;
    case "tunnel": {
      for (let i = 0; i < 24; i++) {
        const a = (i / 24) * Math.PI * 2;
        seg((t) => [0.5 + Math.cos(a) * (0.08 + t * 0.7), 0.5 + Math.sin(a) * (0.08 + t * 0.7)]);
      }
      for (const inset of [0.1, 0.2, 0.3, 0.4]) {
        const a = inset,
          b = 1 - inset;
        out.push([[a, a], [b, a], [b, b], [a, b], [a, a]]);
      }
      break;
    }
  }
  return out;
}

function build(p: Pattern, w: number, h: number): Path[] {
  const bandX = w * 0.12,
    bandY = h * 0.12,
    bar = h * 0.036;
  const inBand = ([x, y]: Pt) =>
    x >= 0 && x <= w && y >= bar && y <= h - bar && (x < bandX || x > w - bandX || y < bandY + bar || y > h - bandY - bar);
  return lines(p).map((raw, key) => {
    // resample to ~3 px steps in screen space
    const pts: Pt[] = [];
    for (let i = 0; i < raw.length - 1; i++) {
      const a: Pt = [raw[i][0] * w, raw[i][1] * h],
        b: Pt = [raw[i + 1][0] * w, raw[i + 1][1] * h];
      const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 3));
      for (let j = 0; j < n; j++) pts.push([a[0] + ((b[0] - a[0]) * j) / n, a[1] + ((b[1] - a[1]) * j) / n]);
    }
    pts.push([raw[raw.length - 1][0] * w, raw[raw.length - 1][1] * h]);
    // draw from the end nearer the centre outward
    const d0 = Math.hypot(pts[0][0] - w / 2, pts[0][1] - h / 2);
    const d1 = Math.hypot(pts[pts.length - 1][0] - w / 2, pts[pts.length - 1][1] - h / 2);
    if (d1 < d0) pts.reverse();
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const windows: [number, number][] = [];
    let start = -1;
    pts.forEach((pt, i) => {
      const ok = inBand(pt);
      if (ok && start < 0) start = cum[i];
      if ((!ok || i === pts.length - 1) && start >= 0) {
        const end = cum[i];
        if (end - start > 40) windows.push([start, end]);
        start = -1;
      }
    });
    return { pts, cum, len: cum[cum.length - 1], windows, key };
  });
}

function strokeRange(ctx: CanvasRenderingContext2D, p: Path, a: number, b: number) {
  a = Math.max(0, a);
  b = Math.min(p.len, b);
  if (b <= a) return;
  ctx.beginPath();
  let started = false;
  for (let i = 0; i < p.pts.length; i++) {
    const c = p.cum[i];
    if (c < a) continue;
    if (c > b) break;
    const [x, y] = p.pts[i];
    const sx = Math.round(x - 0.5) + 0.5,
      sy = Math.round(y - 0.5) + 0.5;
    if (!started) {
      ctx.moveTo(sx, sy);
      started = true;
    } else ctx.lineTo(sx, sy);
  }
  ctx.stroke();
}

export function PatternField({ pattern }: { pattern: Pattern }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const s = useRef({
    w: 0,
    h: 0,
    paths: [] as Path[],
    old: [] as Path[],
    morph: 1,
    events: [] as Event[],
    next: 0.4,
    count: 0,
    pattern,
    ink: "#121211",
    cache: null as HTMLCanvasElement | null, // the still lines, drawn once per layout
  });

  const draw = () => {
    const c = canvas.current;
    const st = s.current;
    if (!c) return;
    const ctx = c.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, st.w, st.h);
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = st.ink;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    const m = st.morph;
    if (m < 1) {
      // old lines retract, new lines grow, each on its own delay and duration
      const T = m; // seconds into a 1 s morph
      st.old.forEach((p) => {
        const r = hash(p.key, 31),
          r2 = hash(p.key, 37);
        const k = easeHouse(Math.min(1, Math.max(0, (T - 0.03 * r) / (0.62 + 0.06 * r2))));
        strokeRange(ctx, p, 0, p.len * (1 - k));
      });
      st.paths.forEach((p) => {
        const r = hash(p.key, 41),
          r2 = hash(p.key, 43);
        const k = easeHouse(Math.min(1, Math.max(0, (T - 0.07 - 0.04 * r) / (0.7 + 0.08 * r2))));
        strokeRange(ctx, p, 0, p.len * k);
      });
      return;
    }
    if (!st.cache) {
      // draw the still lines once; every frame after that is a copy plus the traffic
      const off = document.createElement("canvas");
      off.width = c.width;
      off.height = c.height;
      const o = off.getContext("2d")!;
      o.setTransform(dpr, 0, 0, dpr, 0, 0);
      o.strokeStyle = st.ink;
      o.lineWidth = 1;
      o.lineJoin = "round";
      st.paths.forEach((p) => strokeRange(o, p, 0, p.len));
      st.cache = off;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(st.cache, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // traffic
    for (const e of st.events) {
      const p = st.paths[e.path];
      if (!p) continue;
      const head = e.win[0] + e.t * e.speed;
      if (e.kind === "gap") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = 3;
        const clip = (a: number, b: number) => strokeRange(ctx, p, Math.max(a, e.win[0]), Math.min(b, e.win[1]));
        clip(head - e.len, head);
        for (const tail of e.tails) clip(head - e.len - tail.off - tail.w, head - e.len - tail.off);
        ctx.globalCompositeOperation = "source-over";
        ctx.lineWidth = 1;
      } else {
        ctx.lineWidth = 2;
        strokeRange(ctx, p, Math.max(head - e.len, e.win[0]), Math.min(head, e.win[1]));
        ctx.lineWidth = 1;
      }
    }
  };

  const layout = () => {
    const c = canvas.current,
      el = wrap.current;
    if (!c || !el) return;
    const st = s.current;
    const dpr = window.devicePixelRatio || 1;
    st.w = el.clientWidth;
    st.h = el.clientHeight;
    c.width = Math.round(st.w * dpr);
    c.height = Math.round(st.h * dpr);
    st.ink = getComputedStyle(el).color;
    st.paths = build(st.pattern, st.w, st.h);
    st.events = [];
    st.cache = null;
    draw();
  };

  useEffect(() => {
    layout();
    const ro = new ResizeObserver(layout);
    ro.observe(wrap.current!);
    const mo = new MutationObserver(() => {
      s.current.ink = getComputedStyle(wrap.current!).color;
      s.current.cache = null;
      draw();
    });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      ro.disconnect();
      mo.disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // pattern change: morph
  useEffect(() => {
    const st = s.current;
    if (st.pattern === pattern) return;
    st.pattern = pattern;
    st.old = st.paths;
    st.paths = build(pattern, st.w, st.h);
    st.events = [];
    st.cache = null;
    st.morph = reduced() ? 1 : 0;
    draw();
  }, [pattern]); // eslint-disable-line react-hooks/exhaustive-deps

  useRunWhileVisible(wrap, (dt) => {
    const st = s.current;
    if (st.morph < 1) {
      st.morph = Math.min(1, st.morph + dt);
      draw();
      return;
    }
    // advance and retire events
    const had = st.events.length > 0;
    st.events = st.events.filter((e) => {
      e.t += dt;
      return e.win[0] + e.t * e.speed - e.len - 60 < e.win[1];
    });
    st.next -= dt;
    if (st.next <= 0 && st.events.length < 3) {
      const candidates = st.paths.map((p, i) => ({ p, i })).filter((x) => x.p.windows.length && !st.events.some((e) => e.path === x.i));
      if (candidates.length) {
        const pick = candidates[Math.floor(Math.random() * candidates.length)];
        const win = pick.p.windows[Math.floor(Math.random() * pick.p.windows.length)];
        st.count++;
        const bold = st.count % 3 === 0 || Math.random() < 0.4;
        const speed = 360 + Math.random() * 740;
        const span = win[1] - win[0];
        const len = bold ? Math.min(Math.max(18, Math.min(72, speed / 30)), span * 0.35) : 8 + Math.random() * 112;
        const tails = bold ? [] : Array.from({ length: 1 + Math.floor(Math.random() * 2) }, () => ({ off: 2 + Math.random() * 50, w: 2 + Math.random() * 24 }));
        st.events.push({ path: pick.i, win, kind: bold ? "bold" : "gap", len, speed, t: 0, tails });
        const dur = (span + len) / speed;
        st.next = dur * (0.38 + Math.random() * 0.5);
      } else st.next = 0.2;
    }
    if (had || st.events.length) draw(); // nothing moving: leave the canvas alone
  });

  return (
    <div className="pattern" ref={wrap} aria-hidden>
      <canvas ref={canvas} />
    </div>
  );
}
