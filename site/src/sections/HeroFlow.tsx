import { AnimatePresence, motion } from "motion/react";
import { type CSSProperties, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Icon, reducedMotion } from "../components/ui";

/* -------------------------------------------------------------------------------------------
   The hero flow. Three rows of records ride left to right through a frame. Every ~11 s one
   record is caught: its value turns wrong a few seconds before it reaches the check point
   (30% across), then, at that point, the whole flow slows to 0.45x while the record is checked,
   quoted, decided and fixed. The fix stays. Timings follow a measured reference; see
   site/README.md. Illustration only: the records are made up, the check names are real.
------------------------------------------------------------------------------------------- */

type Kind = "REQ" | "TC" | "SG" | "BO";
type Live = {
  id: string;
  kind: Kind;
  name: string;
  good: string; // the correct value (what the source says)
  bad: string; // the planted mistake
  check: string; // the real Zyn check that catches it
  diag: string;
  quote: string;
  against: "source" | "DBC" | "requirement set";
};
type Slot = Live | null; // null: a blank record (rhythm, never fails)

const ROWS: { speed: number; lead: boolean; slots: Slot[] }[] = [
  {
    speed: 92,
    lead: true,
    slots: [
      { id: "r0", kind: "REQ", name: "REQ-014", good: "warn within 10 ms", bad: "warn within 20 ms", check: "invented_value", diag: "20 ms is not in the source", quote: "\"within 10 ms\"", against: "source" },
      null,
      { id: "r1", kind: "REQ", name: "REQ-017", good: "shall flash twice", bad: "should flash twice", check: "modal_changed", diag: "\"shall\" became \"should\"", quote: "\"shall flash twice\"", against: "source" },
      null,
      { id: "r2", kind: "REQ", name: "REQ-021", good: "dim after 30 s", bad: "dim after 45 s", check: "invented_value", diag: "45 s is not in the source", quote: "\"after 30 s\"", against: "source" },
    ],
  },
  {
    speed: 102,
    lead: true,
    slots: [
      { id: "m0", kind: "TC", name: "TC-201", good: "EngineSpeed > 6000", bad: "EngSpd_Rpm > 6000", check: "unknown_signal", diag: "EngSpd_Rpm is not in the DBC", quote: "EngineSpeed, BO_ 0x1A0", against: "DBC" },
      { id: "m1", kind: "TC", name: "TC-204", good: "2 checks", bad: "0 checks", check: "no_check", diag: "This test can never fail", quote: "the checks of its template", against: "requirement set" },
      null,
      { id: "m2", kind: "TC", name: "TC-206", good: "covers REQ-016", bad: "covers REQ-099", check: "unknown_requirement", diag: "REQ-099 does not exist", quote: "REQ-016 in the set", against: "requirement set" },
      null,
    ],
  },
  {
    speed: 112,
    lead: false,
    slots: [
      null,
      { id: "b0", kind: "SG", name: "Gear", good: "bits 16|4", bad: "bits 8|4", check: "signal_overlap", diag: "Gear shares bits with Mode", quote: "free bits at 16|4", against: "DBC" },
      { id: "b1", kind: "TC", name: "TC-209", good: "FuelLvl = 100", bad: "FuelLvl = 140", check: "out_of_range", diag: "140 is outside 0 to 100", quote: "FuelLvl range 0 to 100", against: "DBC" },
      { id: "b2", kind: "BO", name: "0x2B4", good: "Cluster", bad: "Cluster (0x1A0)", check: "duplicate_frame_id", diag: "0x1A0 is used twice", quote: "the free ID 0x2B4", against: "DBC" },
      null,
    ],
  },
];
const ALL_LIVE = ROWS.flatMap((r) => r.slots.filter(Boolean) as Live[]);
const BLANK_W = [176, 208, 192, 220, 184, 200];

// Phases: investigating, diagnosis, resolution, deciding, success, gap.
const PHASE_MS = [2100, 1400, 1400, 1400, 900, 650];
const EMIT_MS = [36, 40, 45, 51.4];

const hash = (e: number, t: number) => {
  const x = Math.sin((e + 1) * 12.9898 + (t + 1) * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

/* ---------- text scramble: letters lock left to right, 5 ticks of 45 ms ---------- */
const ALPHA = "abcdefghijklmnopqrstuvwxyz";
function useScramble(target: string) {
  const [shown, setShown] = useState(target);
  const prev = useRef(target);
  useEffect(() => {
    const from = prev.current;
    if (from === target) return;
    prev.current = target;
    if (reducedMotion()) {
      setShown(target);
      return;
    }
    // Only characters that differ from the old text tumble; the rest hold still.
    const changed = target.split("").map((c, i) => c !== from[i]);
    let s = 0;
    const id = window.setInterval(() => {
      s += 1;
      if (s > 5) {
        window.clearInterval(id);
        setShown(target);
        return;
      }
      setShown(
        target
          .split("")
          .map((c, i) => {
            if (!changed[i] || i < s - 2 || c === " ") return c;
            const pool = /[0-9]/.test(c) ? "0123456789" : ALPHA;
            return pool[(pool.indexOf(c.toLowerCase()) + 1 + ((3 * s + 5 * i) % 9) + pool.length) % pool.length] ?? c;
          })
          .join(""),
      );
    }, 45);
    return () => window.clearInterval(id);
  }, [target]);
  return shown;
}

/* ---------- engine ---------- */
type Engine = {
  active: string | null;
  errored: string | null;
  phase: number;
  repaired: Set<string>;
};

export function HeroFlow() {
  const surface = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [eng, setEng] = useState<Engine>({ active: null, errored: null, phase: -1, repaired: new Set() });
  const engRef = useRef(eng);
  engRef.current = eng;
  const visible = useRef(false);
  const history = useRef<string[]>([]);
  const timer = useRef<{ id: number; due: number; remaining: number; fn: () => void } | null>(null);
  const rate = useRef(1);
  const still = useMemo(() => reducedMotion(), []);

  /* row widths -> loop distance and duration */
  useLayoutEffect(() => {
    // Records have fixed widths, so a row's loop length only changes with the layout (a resize).
    // The rows start only once measured with the real fonts, and a later change keeps each
    // row's progress, so nothing ever jumps.
    let started = false;
    const fit = () =>
      rowRefs.current.forEach((row, i) => {
        if (!row) return;
        const copy = row.firstElementChild as HTMLElement;
        const w = copy.offsetWidth;
        if (row.style.getPropertyValue("--row-width") === `${w}px`) return;
        const anim = row.getAnimations()[0];
        const frac = anim && anim.effect ? Number(anim.currentTime ?? 0) / Number(anim.effect.getTiming().duration || 1) : 0;
        row.style.setProperty("--row-width", `${w}px`);
        row.style.animationDuration = `${w / ROWS[i].speed}s`;
        const next = row.getAnimations()[0];
        if (next && started) next.currentTime = (frac % 1) * (w / ROWS[i].speed) * 1000;
      });
    const start = () => {
      fit();
      started = true;
      surface.current?.setAttribute("data-ready", "");
    };
    if (document.fonts?.status === "loaded") start();
    else document.fonts?.ready.then(start);
    let t = 0;
    const onResize = () => {
      window.clearTimeout(t);
      t = window.setTimeout(fit, 120);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  /* playback rate of every CSS animation in the rows and side wires */
  const tweenId = useRef(0);
  const tweenRate = useCallback((to: number, ms: number, delay = 0) => {
    const root = surface.current;
    if (!root) return;
    cancelAnimationFrame(tweenId.current); // one tween at a time: a new one takes over smoothly
    const anims = [...root.querySelectorAll<HTMLElement>(".flow__row, .flow__wires")].flatMap((el) => el.getAnimations({ subtree: true }));
    const from = rate.current;
    const t0 = performance.now() + delay;
    // HOUSE-like ease for slowing down, quart-out for speeding back up
    const ease = to < from ? (t: number) => 1 - Math.pow(1 - t, 2.2) : (t: number) => 1 - Math.pow(1 - t, 4);
    const step = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - t0) / ms));
      rate.current = from + (to - from) * ease(t);
      for (const a of anims) a.updatePlaybackRate ? a.updatePlaybackRate(rate.current) : (a.playbackRate = rate.current);
      if (t < 1) tweenId.current = requestAnimationFrame(step);
    };
    tweenId.current = requestAnimationFrame(step);
  }, []);

  /* pausable phase timer */
  const schedule = useCallback((ms: number, fn: () => void) => {
    if (timer.current) window.clearTimeout(timer.current.id);
    const t = { id: 0, due: performance.now() + ms, remaining: ms, fn };
    if (visible.current) t.id = window.setTimeout(fn, ms);
    timer.current = t;
  }, []);

  const runPhase = useCallback(
    (p: number) => {
      setEng((e) => ({ ...e, phase: p }));
      if (p === 0) tweenRate(0.45, 500, 40);
      if (p === 5) tweenRate(1, 180);
      schedule(PHASE_MS[p], () => {
        if (p === 4) {
          setEng((e) => {
            const repaired = new Set(e.repaired);
            if (e.active) repaired.add(e.active);
            return { ...e, repaired, errored: null };
          });
          runPhase(5);
        } else if (p === 5) {
          timer.current = null;
          setEng((e) => ({ ...e, active: null, phase: -1 }));
        } else runPhase(p + 1);
      });
    },
    [schedule, tweenRate],
  );

  /* selection and activation loop */
  useEffect(() => {
    if (still) return;
    let raf = 0;
    let lastTravel = Infinity;
    const geometry = () => {
      const f = frame.current!.getBoundingClientRect();
      const anchor = f.left + Math.max(0.3 * f.width, Math.min(f.width / 2, 175));
      return { f, anchor };
    };
    const travelOf = (id: string, anchor: number) => {
      const el = surface.current?.querySelector<HTMLElement>(`[data-copy="0"] [data-live="${id}"]`);
      const row = el?.closest<HTMLElement>(".flow__row");
      if (!el || !row) return null;
      const r = el.getBoundingClientRect();
      const rowW = parseFloat(row.style.getPropertyValue("--row-width")) || 1;
      const speed = ROWS[Number(row.dataset.row)].speed;
      const cx = r.left + r.width / 2;
      const travel = (((anchor - cx) % rowW) + rowW) % rowW;
      return { travel, lead: travel / speed, left: r.left };
    };
    const tick = () => {
      raf = requestAnimationFrame(tick);
      if (!visible.current || !frame.current) return;
      const e = engRef.current;
      const { f, anchor } = geometry();
      if (!e.active && !e.errored) {
        const recent = history.current[history.current.length - 1];
        const cands = ALL_LIVE.filter((c) => c.id !== recent)
          .map((c) => ({ c, t: travelOf(c.id, anchor) }))
          .filter((x) => x.t) as { c: Live; t: { lead: number } }[];
        const age = (id: string) => {
          const i = history.current.lastIndexOf(id);
          return i < 0 ? -1 : i;
        };
        const window_ = cands.filter((x) => x.t.lead >= 2.5 && x.t.lead <= 5).sort((a, b) => age(a.c.id) - age(b.c.id) || a.t.lead - b.t.lead);
        const pick =
          window_[0] ??
          cands.filter((x) => x.t.lead >= 2.5).sort((a, b) => a.t.lead - b.t.lead)[0] ??
          cands.sort((a, b) => b.t.lead - a.t.lead)[0];
        if (pick) {
          lastTravel = Infinity;
          setEng((s) => ({ ...s, errored: pick.c.id }));
        }
        return;
      }
      if (e.errored && !e.active) {
        const t = travelOf(e.errored, anchor);
        if (!t) return;
        const wrapped = t.travel > lastTravel + 1 && t.left < f.right;
        lastTravel = t.travel;
        if (t.travel <= 6 || wrapped) {
          history.current.push(e.errored);
          setEng((s) => ({ ...s, active: s.errored }));
          runPhase(0);
        }
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [runPhase, still]);

  /* run only on screen (and with the tab visible); timers resume where they stopped */
  useEffect(() => {
    const el = surface.current!;
    let onScreen = false;
    const apply = () => {
      const v = onScreen && document.visibilityState === "visible";
      if (v === visible.current) return;
      visible.current = v;
      if (v) el.setAttribute("data-visible", "");
      else el.removeAttribute("data-visible");
      const t = timer.current;
      if (!t) return;
      if (v) {
        t.due = performance.now() + t.remaining;
        t.id = window.setTimeout(t.fn, t.remaining);
      } else {
        window.clearTimeout(t.id);
        t.remaining = Math.max(0, t.due - performance.now());
      }
    };
    const io = new IntersectionObserver(([e]) => {
      onScreen = e.isIntersecting;
      apply();
    });
    io.observe(el);
    document.addEventListener("visibilitychange", apply);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", apply);
      if (timer.current) window.clearTimeout(timer.current.id);
    };
  }, []);

  const rows = ROWS.map((row, ri) => {
    const unit = (copy: number) => (
      <div className="flow__copy" data-copy={copy} key={copy}>
        {row.slots.map((slot, si) => (
          <span className="flow__unit" key={si}>
            {(row.lead || si > 0) && <span className="flow__rule" aria-hidden />}
            {slot ? (
              <Record live={slot} eng={eng} />
            ) : (
              <span className="rec rec--blank" style={{ width: BLANK_W[(ri * 2 + si) % BLANK_W.length] }}>
                <span className="rec__kind" />
                <span className="rec__text" />
                <span className="rec__status" />
              </span>
            )}
            {!row.lead && si === row.slots.length - 1 && <span className="flow__rule" aria-hidden />}
          </span>
        ))}
      </div>
    );
    return (
      <div
        key={ri}
        className="flow__row"
        data-row={ri}
        data-hot={eng.active && row.slots.some((s) => s?.id === eng.active) ? "" : undefined}
        style={{ "--row-top": `${99 + ri * 100}px` } as CSSProperties}
        ref={(el) => {
          rowRefs.current[ri] = el;
        }}
      >
        {unit(0)}
        {unit(1)}
      </div>
    );
  });

  return (
    <div
      className={`flow ${still ? "flow--still" : ""}`}
      ref={surface}
      role="img"
      aria-label="Illustration: requirement, test and CAN records flow through Zyn. One at a time, a planted mistake is caught by a code check, quoted from its source, decided by a person and fixed."
    >
      <SideWires side="left" />
      <div className="flow__frame" ref={frame}>
        <span className="flow__tag">
          <Icon name="running" size={14} className="spin-steps" />
          Checking
        </span>
        {[49, 149, 249, 349].map((y) => (
          <span key={y} className="flow__dots" style={{ top: y }} aria-hidden />
        ))}
        {rows}
      </div>
      <SideWires side="right" />
    </div>
  );
}

/* ---------- one record ---------- */
function Record({ live, eng }: { live: Live; eng: Engine }) {
  const isActive = eng.active === live.id;
  const isErrored = eng.errored === live.id;
  const repaired = eng.repaired.has(live.id);
  const phase = isActive ? eng.phase : -1;
  const working = isActive && phase >= 0 && phase <= 3;
  const success = isActive && phase === 4;
  const highlighted = isActive && phase >= 0 && phase <= 4;

  const showBad = (isErrored || working) && !success;
  const text = useScramble(showBad ? live.bad : live.good);
  const status = useScramble(showBad ? "flag" : repaired || success ? "fixed" : "no flag");

  return (
    <span className="rec-slot" data-live={live.id}>
      <span
        className="rec"
        data-state={highlighted ? (success ? "success" : "working") : isErrored ? "errored" : repaired ? "fixed" : "idle"}
        data-vibrate={phase === 0 ? "" : undefined}
      >
        <span className="rec__kind">{live.kind}</span>
        <span className="rec__name">{live.name}</span>
        <span className="rec__text" style={{ width: `${Math.max(live.good.length, live.bad.length)}ch` }}>
          {text}
        </span>
        <span className="rec__dot" aria-hidden>
          ·
        </span>
        <span className="rec__status">{status}</span>
      </span>
      {highlighted && <Sparks phase={phase} />}
      <AnimatePresence>{isActive && phase >= 0 && phase <= 4 && <Tip key="tip" live={live} phase={phase} />}</AnimatePresence>
    </span>
  );
}

/* ---------- the popup above the record ---------- */
const HOUSE = [0.6, 0.6, 0, 1] as const;
const QUART = [0.165, 0.84, 0.44, 1] as const;
const SHARP = [0.9, 0, 0.1, 1] as const;

function steps(l: Live) {
  return [
    { icon: "running", title: `Checking against the ${l.against}...`, detail: "Code check: same result every run" },
    { icon: "failed", title: l.check, detail: l.diag },
    { icon: "ai-reviewer", title: "Source words found", detail: `${l.quote}, quoted by the AI reviewer` },
    { icon: "person", title: "Waiting for a named person", detail: "One key to approve the fix" },
    { icon: "passed", title: "Approved and fixed", detail: "Written to the audit log" },
  ];
}

function Tip({ live, phase }: { live: Live; phase: number }) {
  const s = steps(live)[phase];
  return (
    <motion.span
      className="tip"
      initial={{ opacity: 0, y: 9, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1, transition: { opacity: { delay: 0.1, duration: 0.28, ease: QUART }, default: { delay: 0.04, duration: 0.5, ease: HOUSE } } }}
      exit={{ opacity: 0, y: -3, scale: 0.99, transition: { opacity: { duration: 0.1, ease: SHARP }, default: { duration: 0.18, ease: QUART } } }}
      style={{ originX: 0.5, originY: 1 }}
    >
      <Ripple key={`r${phase}`} />
      <AnimatePresence initial={false}>
        <motion.span
          key={phase}
          className="tip__row"
          initial="hide"
          animate="show"
          exit="gone"
          variants={{ show: { transition: { delayChildren: 0.08, staggerChildren: 0.025 } }, gone: { transition: { staggerChildren: 0.015, staggerDirection: -1 } } }}
        >
          <motion.span className="tip__icon" variants={child}>
            <Icon name={s.icon} size={18} className={phase === 0 ? "spin" : ""} />
          </motion.span>
          <span className="tip__col">
            <motion.span className={`tip__title ${phase === 1 ? "tip__title--mono" : ""}`} variants={child}>
              {phase === 0 ? <Shimmer text={s.title} /> : s.title}
            </motion.span>
            <motion.span className="tip__detail" variants={child}>
              {s.detail}
            </motion.span>
          </span>
        </motion.span>
      </AnimatePresence>
    </motion.span>
  );
}

const child = {
  hide: { opacity: 0, y: 3 },
  show: { opacity: 1, y: 0, transition: { opacity: { duration: 0.12, ease: QUART }, y: { duration: 0.18, ease: QUART } } },
  gone: { opacity: 0, y: -2, transition: { opacity: { duration: 0.06, ease: SHARP }, y: { duration: 0.1, ease: QUART } } },
};

/** A hard-stepped highlight about three letters wide, sweeping every 1.35 s. */
function Shimmer({ text }: { text: string }) {
  return (
    <span className="shimmer" aria-label={text}>
      {text.split("").map((c, i) => (
        <span key={i} aria-hidden style={{ animationDelay: `${i * 65}ms` }}>
          {c === " " ? " " : c}
        </span>
      ))}
    </span>
  );
}

/** A faint ripple of 5 px cells from the icon, on every step change. */
function Ripple() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c || reducedMotion()) return;
    const ctx = c.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    const W = 272,
      H = 64;
    c.width = W * dpr;
    c.height = H * dpr;
    ctx.scale(dpr, dpr);
    const cells: { x: number; y: number; on: number; off: number }[] = [];
    let k = 0;
    for (let x = 0; x < W; x += 5)
      for (let y = 0; y < H; y += 5) {
        const d = Math.hypot(x - 20, y - 22);
        k++;
        if (d > 108 || hash(k, 7) > 0.28) continue;
        const on = (d / 108) * 300 + 80 * hash(k, 9);
        cells.push({ x, y, on, off: on + 80 + 120 * hash(k, 11) });
      }
    const t0 = performance.now();
    const id = window.setInterval(() => {
      const t = performance.now() - t0;
      ctx.clearRect(0, 0, W, H);
      if (t > 520) {
        window.clearInterval(id);
        return;
      }
      ctx.fillStyle = "rgba(255,255,255,.09)";
      for (const cell of cells) if (t >= cell.on && t < cell.off) ctx.fillRect(cell.x, cell.y, 4, 4);
    }, 60);
    return () => window.clearInterval(id);
  }, []);
  return <canvas ref={ref} className="tip__ripple" aria-hidden />;
}

/* ---------- sparks: stepped pixel squares that blink along a short spiral ---------- */
type Spark = { id: number; style: CSSProperties };
let sparkSeq = 0;
function makeSpark(): Spark {
  const id = ++sparkSeq;
  const h = (k: number) => hash(id, k);
  const ang = h(1) * Math.PI * 2;
  const dx = Math.cos(ang),
    dy = Math.sin(ang);
  const halfW = 118,
    halfH = 28;
  const scale = 1 / Math.max(Math.abs(dx) / halfW, Math.abs(dy) / halfH);
  const r0 = scale;
  const r1 = scale * (1.18 + 0.34 * h(2));
  const turn = (0.12 + 0.5 * h(3)) * (h(4) < 0.5 ? -1 : 1);
  const at = (f: number) => {
    const r = r0 + (r1 - r0) * f;
    const a = ang + turn * f;
    return [Math.cos(a) * r, Math.sin(a) * r * (halfH / halfW) * 1.6];
  };
  const [sx, sy] = [dx * scale, dy * scale * (halfH / halfW) * 1.6];
  const [m1x, m1y] = at(0.45);
  const [m2x, m2y] = at(0.78);
  const [ex, ey] = at(1);
  const size = 2 + Math.round(6 * h(5));
  const style = {
    width: size,
    height: size,
    "--sx": `${sx}px`,
    "--sy": `${sy}px`,
    "--m1x": `${m1x}px`,
    "--m1y": `${m1y}px`,
    "--m2x": `${m2x}px`,
    "--m2y": `${m2y}px`,
    "--ex": `${ex}px`,
    "--ey": `${ey}px`,
    animationDuration: `${0.68 + 0.5 * h(6)}s`,
    animationDelay: `${Math.round(80 * h(7))}ms`,
    animationTimingFunction: `steps(${3 + Math.floor(4 * h(8))}, jump-end)`,
  } as CSSProperties;
  return { id, style };
}

function Sparks({ phase }: { phase: number }) {
  const [sparks, setSparks] = useState<Spark[]>([]);
  const add = useCallback((n: number) => setSparks((s) => [...s, ...Array.from({ length: n }, makeSpark)]), []);
  useEffect(() => {
    if (reducedMotion()) return;
    add(14);
  }, [add]);
  useEffect(() => {
    if (reducedMotion()) return;
    if (phase >= 1 && phase <= 4) add(3);
    if (phase > 3) return;
    const id = window.setInterval(() => add(1), EMIT_MS[phase]);
    return () => window.clearInterval(id);
  }, [phase, add]);
  return (
    <span className="sparks" aria-hidden>
      {sparks.map((s) => (
        <i key={s.id} style={s.style} onAnimationEnd={() => setSparks((all) => all.filter((x) => x.id !== s.id))} />
      ))}
    </span>
  );
}

/* ---------- side wires: the rows continue outside the frame, to the page edge ---------- */
function SideWires({ side }: { side: "left" | "right" }) {
  const wires = useMemo(() => {
    const rowOf = [0, 0, 1, 1, 1, 2, 2];
    return rowOf.map((row, w) => {
      const key = w + (side === "right" ? 10000 : 0);
      const segs: { width: number; dashed: boolean; gap: number }[] = [];
      for (let s = 0; s < 6; s++) {
        const k = key * 6 + s;
        segs.push({ dashed: hash(k, 0) < 0.5, width: 44 + Math.round(112 * hash(k, 1)), gap: 64 + Math.round(40 * hash(k, 2)) });
      }
      const period = segs.reduce((a, s) => a + s.width + s.gap, 0);
      const dur = period / ROWS[row].speed;
      return { y: 50 + w * 50, segs, period, dur, delay: -dur * hash(key, 3) };
    });
  }, [side]);
  return (
    <div className={`flow__wires flow__wires--${side}`} aria-hidden>
      {wires.map((w, i) => (
        <div
          key={i}
          className="wire"
          style={{ top: w.y, width: w.period * 3, "--period": `${w.period}px`, animationDuration: `${w.dur}s`, animationDelay: `${w.delay}s` } as CSSProperties}
        >
          {[0, 1, 2].flatMap((rep) =>
            w.segs.map((s, j) => (
              <span key={`${rep}-${j}`} className={`wire__seg ${s.dashed ? "wire__seg--dots" : ""}`} style={{ width: s.width, marginRight: s.gap }} />
            )),
          )}
        </div>
      ))}
    </div>
  );
}
