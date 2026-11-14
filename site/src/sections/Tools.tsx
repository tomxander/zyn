import { AnimatePresence, motion } from "motion/react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { HUB_IN, HUB_OUT, TOOLS } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";
import { docHref } from "../docs/docs";
import { HOUSE, QUART, reduced, useRunWhileVisible } from "../components/runtime";

type Wire = { name: string; d: string; out: boolean };
type Flow = {
  name: string;
  phase: "draw" | "stream" | "retract";
  drawn: number;
  pos: number;
  dir: 1 | -1;
  wait: number;
  life: number;
  pace: number;
  len: number;
};
const SPEED = 900; // px/s for lines and packets
const ADVANCE = 7;

/**
 * The tools hub. What a tool reads is on the left, what it writes on the right. Every 0.5 to
 * 1.5 s one of the tool's tiles comes alive: its wire draws out from the tool at 900 px/s, a
 * packet shuttles between tool and tile, the tile turns ink once hit, each impact throws a
 * small pixel burst, and after 3 to 5 s the wire retracts.
 */
export function Tools() {
  const [active, setActive] = useState(0);
  const tool = TOOLS[active];
  const hub = useRef<HTMLDivElement>(null);
  const burst = useRef<HTMLCanvasElement>(null);
  const [wires, setWires] = useState<Wire[]>([]);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [flows, setFlows] = useState<string[]>([]);
  const [hit, setHit] = useState<Record<string, boolean>>({});
  const flowState = useRef(new Map<string, Flow>());
  const els = useRef(new Map<string, { path: SVGPathElement | null; packet: HTMLSpanElement | null }>());
  const sched = useRef({ next: 0.3, clock: 0, recent: [] as string[] });
  const cells = useRef<{ x: number; y: number; on: number; off: number }[]>([]);
  const burstClock = useRef(0);

  // tile keys carry their side ("i:ReqIF", "o:ReqIF"): some formats are read and written
  const live = useCallback((key: string, out: boolean) => (out ? tool.outputs : tool.inputs).includes(key.slice(2)), [tool]);

  /* measure: wires from the tool core to each tile, right angles through a bus on each side */
  useLayoutEffect(() => {
    const root = hub.current;
    if (!root) return;
    const measure = () => {
      const box = root.getBoundingClientRect();
      const rel = (el: Element) => {
        const r = el.getBoundingClientRect();
        return { l: r.left - box.left, r: r.right - box.left, t: r.top - box.top, b: r.bottom - box.top };
      };
      const core = rel(root.querySelector(".hub__core")!);
      const cy = Math.round((core.t + core.b) / 2) + 0.5;
      const ins = Array.from(root.querySelectorAll<HTMLElement>(".hub__tile--in"));
      const outs = Array.from(root.querySelectorAll<HTMLElement>(".hub__tile--out"));
      const busL = Math.round((rel(ins[0]).r + core.l) / 2) + 0.5;
      const busR = Math.round((rel(outs[0]).l + core.r) / 2) + 0.5;
      const next: Wire[] = [];
      ins.forEach((el) => {
        const r = rel(el);
        const y = Math.round((r.t + r.b) / 2) + 0.5;
        next.push({ name: el.dataset.name!, out: false, d: `M${Math.round(core.l)} ${cy} H${busL} V${y} H${Math.round(r.r)}` });
      });
      outs.forEach((el) => {
        const r = rel(el);
        const y = Math.round((r.t + r.b) / 2) + 0.5;
        next.push({ name: el.dataset.name!, out: true, d: `M${Math.round(core.r)} ${cy} H${busR} V${y} H${Math.round(r.l)}` });
      });
      setWires(next);
      setSize({ w: Math.round(box.width), h: Math.round(box.height) });
      if (burst.current) {
        const dpr = window.devicePixelRatio || 1;
        burst.current.width = Math.round(box.width * dpr);
        burst.current.height = Math.round(box.height * dpr);
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(root);
    return () => ro.disconnect();
  }, []);

  /* a new tool: running wires retract (no cut), then the new tool's tiles come alive */
  useLayoutEffect(() => {
    for (const f of flowState.current.values()) f.phase = "retract";
    sched.current.next = 0.45;
  }, [active]);

  const impact = (name: string, atTile: boolean) => {
    const w = wires.find((x) => x.name === name);
    const el = els.current.get(name)?.path;
    if (!w || !el) return;
    const p = el.getPointAtLength(atTile ? el.getTotalLength() : 0);
    for (let x = -16; x <= 16; x += 4)
      for (let y = -16; y <= 16; y += 4) {
        const d = Math.hypot(x, y);
        if (d > 16 || Math.random() > 0.34) continue;
        const on = burstClock.current + (d / 16) * 0.052 + Math.random() * 0.07;
        cells.current.push({ x: p.x + x, y: p.y + y, on, off: on + 0.07 + Math.random() * 0.1 });
      }
  };

  useRunWhileVisible(hub, (dt) => {
    const s = sched.current;
    burstClock.current += dt;
    // tool auto-advance
    s.clock += dt;
    if (s.clock >= ADVANCE) {
      s.clock = 0;
      setActive((a) => (a + 1) % TOOLS.filter((t) => !t.planned).length);
      return;
    }
    if (tool.planned) return;
    // schedule a new flow
    s.next -= dt;
    const candidates = wires.filter((w) => live(w.name, w.out) && !flowState.current.has(w.name));
    if (s.next <= 0 && candidates.length) {
      s.next = 0.5 + Math.random();
      const fresh = candidates.filter((c) => !s.recent.includes(c.name));
      const pool = fresh.length ? fresh : candidates;
      const pick = pool[Math.floor(Math.random() * pool.length)];
      s.recent = [...s.recent.slice(-2), pick.name];
      flowState.current.set(pick.name, { name: pick.name, phase: "draw", drawn: 0, pos: 0, dir: 1, wait: 0, life: 3 + Math.random() * 2, pace: 0.8 + Math.random() * 0.45, len: 0 });
      setFlows([...flowState.current.keys()]);
    }
    // advance flows
    let changed = false;
    for (const f of flowState.current.values()) {
      const el = els.current.get(f.name);
      if (!el?.path) continue;
      if (!f.len) f.len = el.path.getTotalLength();
      f.life -= dt;
      if (f.phase === "draw") {
        f.drawn = Math.min(f.len, f.drawn + SPEED * dt);
        if (f.drawn >= f.len) f.phase = "stream";
      } else if (f.phase === "stream") {
        if (f.wait > 0) f.wait -= dt;
        else {
          f.pos += f.dir * SPEED * f.pace * dt;
          if (f.dir === 1 && f.pos >= f.len) {
            f.pos = f.len;
            f.dir = -1;
            f.wait = 0.22;
            impact(f.name, true);
            if (!hit[f.name]) {
              setHit((h) => ({ ...h, [f.name]: true }));
            }
          } else if (f.dir === -1 && f.pos <= 0) {
            f.pos = 0;
            f.dir = 1;
            f.wait = 0.22;
            impact(f.name, false);
            if (f.life <= 0) f.phase = "retract";
          }
        }
      } else {
        f.drawn = Math.max(0, f.drawn - SPEED * dt);
        if (f.drawn <= 0) {
          flowState.current.delete(f.name);
          changed = true;
          setHit((h) => ({ ...h, [f.name]: false }));
          continue;
        }
      }
      el.path.style.strokeDasharray = `${f.drawn} ${f.len + 10}`;
      if (el.packet) {
        const show = f.phase === "stream";
        el.packet.style.opacity = show ? "1" : "0";
        el.packet.style.offsetDistance = `${Math.max(0, Math.min(f.len, f.pos))}px`;
      }
    }
    if (changed) setFlows([...flowState.current.keys()]);
    // pixel bursts at ~16 fps
    const c = burst.current;
    if (c) {
      const ctx = c.getContext("2d")!;
      const dpr = window.devicePixelRatio || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, c.width, c.height);
      const now = burstClock.current;
      cells.current = cells.current.filter((cell) => cell.off > now);
      ctx.fillStyle = getComputedStyle(c).color;
      for (const cell of cells.current) if (now >= cell.on) ctx.fillRect(Math.round(cell.x), Math.round(cell.y), 3, 3);
    }
  }, !reduced());

  const select = (i: number) => {
    sched.current.clock = 0;
    setActive(i);
  };

  return (
    <section id="tools" className="section" data-sa="3" aria-labelledby="tools-title">
      <div className="wrap">
        <SectionHead>The tools</SectionHead>
      </div>
      <div className="wrap split split--tools">
        <div className="split__text">
          <Headline id="tools-title" plain="One checker," inked="for the work AI writes." />
          <p className="body">Bring the files you already have. Zyn checks them and hands back the formats your tools expect.</p>
          <ul className="toollist" role="list">
            {TOOLS.map((t, i) => (
              <li key={t.id}>
                <button
                  type="button"
                  className="toollist__item"
                  aria-pressed={i === active}
                  onClick={() => select(i)}
                  data-planned={t.planned || undefined}
                >
                  <Icon name={t.mark} size={20} />
                  <span className="toollist__name">
                    <span className="toollist__hl">{t.name}</span>
                  </span>
                  <span className="toollist__text">{t.text}</span>
                  <Icon name="chevron-right" size={12} className="toollist__chev" />
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="hubpanel field--sa" data-sa={3}>
          <span className="panel__bar panel__bar--top hubpanel__bar" aria-hidden />
          <span className="panel__bar panel__bar--bottom hubpanel__bar" aria-hidden />
          <div
            className="hub"
            ref={hub}
            role="img"
            aria-label={
              tool.planned
                ? `${tool.name} is planned and not built yet.`
                : `${tool.name} reads ${tool.inputs.join(", ")} and writes ${tool.outputs.join(", ")}.`
            }
          >
            <svg className="hub__svg" width={size.w} height={size.h} viewBox={`0 0 ${size.w} ${size.h}`} aria-hidden>
              {wires.map((w) => (
                <path key={`base-${w.name}`} className="hub__wire hub__wire--base" data-on={live(w.name, w.out) || undefined} d={w.d} />
              ))}
              {wires
                .filter((w) => flows.includes(w.name))
                .map((w) => (
                  <path
                    key={`flow-${w.name}`}
                    className="hub__wire is-live"
                    d={w.d}
                    style={{ strokeDasharray: "0 9999" }}
                    ref={(el) => {
                      const cur = els.current.get(w.name) ?? { path: null, packet: null };
                      cur.path = el;
                      els.current.set(w.name, cur);
                    }}
                  />
                ))}
            </svg>
            {wires
              .filter((w) => flows.includes(w.name))
              .map((w) => (
                <span
                  key={`p-${w.name}`}
                  className="hub__packet"
                  style={{ offsetPath: `path("${w.d}")`, opacity: 0 }}
                  ref={(el) => {
                    const cur = els.current.get(w.name) ?? { path: null, packet: null };
                    cur.packet = el;
                    els.current.set(w.name, cur);
                  }}
                  aria-hidden
                />
              ))}
            <canvas ref={burst} className="hub__burst" aria-hidden />

            <div className="hub__col hub__col--in">
              <span className="hub__col-label">Reads</span>
              {HUB_IN.map((x) => (
                <span key={x} className="hub__tile hub__tile--in" data-name={`i:${x}`} data-live={live(`i:${x}`, false) ? "1" : "0"} data-hit={hit[`i:${x}`] || undefined}>
                  {x}
                </span>
              ))}
            </div>

            <div className="hub__mid">
              <a className="hub__core" href={tool.planned ? undefined : docHref(tool.id)} aria-label={`Read about ${tool.name}`}>
                <AnimatePresence mode="popLayout" initial={false}>
                  <motion.span
                    key={tool.id}
                    className="hub__core-in"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0, transition: { duration: 0.35, ease: HOUSE } }}
                    exit={{ opacity: 0, y: -8, transition: { duration: 0.18, ease: QUART } }}
                  >
                    <Icon name={tool.mark} size={40} />
                    <span className="hub__core-name">{tool.name}</span>
                    <span className="hub__core-planned">{tool.planned ? "planned" : "read more"}</span>
                  </motion.span>
                </AnimatePresence>
              </a>
            </div>

            <div className="hub__col hub__col--out">
              <span className="hub__col-label">Writes</span>
              {HUB_OUT.map((x) => (
                <span key={x} className="hub__tile hub__tile--out" data-name={`o:${x}`} data-live={live(`o:${x}`, true) ? "1" : "0"} data-hit={hit[`o:${x}`] || undefined}>
                  {x}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
