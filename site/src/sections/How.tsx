import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { LAYERS, type Layer } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";
import { Panel } from "../components/Panel";
import type { Pattern } from "../components/PatternField";
import { HOUSE, QUART, reduced, useRunWhileVisible, useVisibleClock } from "../components/runtime";

const PATTERNS: Pattern[] = ["fisheye", "mesh", "bow", "tunnel"];
const ADVANCE = 8; // seconds of visible time per layer

export function How() {
  const [open, setOpen] = useState(0);
  const list = useRef<HTMLDivElement>(null);
  const clock = useRef(0);
  useRunWhileVisible(list, (dt) => {
    clock.current += dt;
    if (clock.current >= ADVANCE) {
      clock.current = 0;
      setOpen((o) => (o + 1) % LAYERS.length);
    }
  });
  const select = (i: number) => {
    clock.current = 0;
    setOpen(i);
  };
  const onKey = (e: React.KeyboardEvent) => {
    const k = e.key;
    const next = k === "ArrowDown" ? open + 1 : k === "ArrowUp" ? open - 1 : k === "Home" ? 0 : k === "End" ? LAYERS.length - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const i = (next + LAYERS.length) % LAYERS.length;
    select(i);
    (list.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[i])?.focus();
  };

  return (
    <section id="how" className="section" data-sa="1" aria-labelledby="how-title">
      <div className="wrap">
        <SectionHead>How it works</SectionHead>
      </div>
      <div className="wrap split split--flip">
        <Panel sa={1} pattern={PATTERNS[open]}>
          <div className="swap">
            <AnimatePresence initial={false}>
              <LayerCard key={LAYERS[open].id} layer={LAYERS[open]} />
            </AnimatePresence>
          </div>
        </Panel>

        <div className="split__text">
          <Headline id="how-title" plain="Machines flag it." inked="A person decides." />
          <p className="body">
            Code compares the work with its source and never guesses. An AI reviewer adds advice, only with a quote you can
            check. Then an engineer decides, and the record remembers who and when.
          </p>
          <div className="vtabs" role="tablist" aria-orientation="vertical" ref={list} onKeyDown={onKey}>
            {LAYERS.map((l, i) => (
              <div key={l.id} className="vtab" data-open={i === open || undefined}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={i === open}
                  tabIndex={i === open ? 0 : -1}
                  className="vtab__btn"
                  onClick={() => select(i)}
                >
                  <Icon name={l.icon} size={20} />
                  <span className="vtab__title">{l.title}</span>
                  <span className="vtab__short">{l.short}</span>
                </button>
                <div className="vtab__body" aria-hidden={i !== open}>
                  <div className="vtab__inner">
                    <p>{l.text}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}


const SPIN = ["-", "\\", "|", "/"];

/** The record card on the panel: comes in, works (spinner), the record block opens, done. */
function LayerCard({ layer }: { layer: Layer }) {
  const ref = useRef<HTMLDivElement>(null);
  const t = useVisibleClock(ref, 3.4) - 0.5; // starts 0.5 s after first seen
  const still = reduced();
  const working = !still && t >= 0.45 && t < 2.9;
  const open = still || t >= 1.35;
  const done = still || t >= 2.9;
  return (
    <motion.div
      ref={ref}
      className="sheet sheet--ink sheet--code"
      initial={{ opacity: 0, y: 8 }}
      animate={t >= 0.1 || still ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
      exit={{ opacity: 0, y: -8, transition: { duration: 0.28, ease: QUART } }}
      transition={{ duration: 0.35, ease: HOUSE }}
    >
      <div className="sheet__head">
        <span className="sheet__method">REQ-014</span>
        <span className="sheet__path">The cluster shall show the warning within 10 ms.</span>
        <span className="sheet__spin" aria-hidden>
          {done ? <Icon name="passed" size={14} /> : working ? SPIN[Math.floor((t - 0.45) / 0.11) % 4] : ""}
        </span>
      </div>
      <motion.dl
        className="record"
        initial={false}
        animate={{ height: open ? "auto" : 38 }}
        transition={{ duration: 0.48, ease: HOUSE }}
      >
        <span className="record__brace">{"{"}</span>
        <motion.div
          className="record__band"
          initial={false}
          animate={{ opacity: open ? 1 : 0 }}
          transition={{ duration: 0.3, ease: QUART }}
        >
          {layer.record.map((r) => (
            <div key={r.k} className="record__row">
              <dt>{r.k}</dt>
              <dd data-tone={r.tone}>{r.v}</dd>
            </div>
          ))}
        </motion.div>
        <span className="record__brace">{"}"}</span>
      </motion.dl>
      <div className="sheet__foot sheet__foot--row">
        <Icon name={layer.icon} size={16} />
        {layer.title}: {layer.short.toLowerCase()}
      </div>
    </motion.div>
  );
}
