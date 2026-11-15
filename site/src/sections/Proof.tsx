import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { AI_REVIEW, CAUGHT, type ProofRow, REAL_DBC, STOPS, TEMPLATES } from "../content";
import { Headline, SectionHead } from "../components/ui";
import { docHref } from "../docs/docs";
import type { Pattern } from "../components/PatternField";
import { PatternField } from "../components/PatternField";
import { HOUSE, QUART, useRunWhileVisible } from "../components/runtime";

const SETS: { id: string; label: string; pattern: Pattern; rows: ProofRow[]; head: string; foot: string }[] = [
  {
    id: "code",
    label: "Caught by code",
    pattern: "arcs",
    rows: CAUGHT,
    head: "Planted mistake",
    foot: "False alarms on the clean originals: 0 of 156 requirements. 3 of 43 tests, all for values the test had assumed.",
  },
  {
    id: "stops",
    label: "Where code stops",
    pattern: "fan",
    rows: STOPS,
    head: "Planted mistake",
    foot: "Zyn says where code alone is not enough, and what catches the mistake instead.",
  },
  {
    id: "templates",
    label: "Template tests",
    pattern: "lattice",
    rows: TEMPLATES,
    head: "31 injected faults, seven requirements",
    foot: "More tests did not mean more coverage. The same model asked twice wrote a different test set. The largest model was no better than the middle one. Across all 15 requirements, templates caught 66 of 67 faults with 43 tests; free-written tests caught 31 to 44 with 99 to 121.",
  },
  {
    id: "real",
    label: "Real CAN files",
    pattern: "mesh",
    rows: REAL_DBC,
    head: "comma.ai opendbc: 58 public CAN databases",
    foot: "No answer key exists for real files, so this is not a precision figure. Also found: 191 messages with signals sharing bits, 85 undeclared nodes.",
  },
  {
    id: "ai",
    label: "The AI reviewer",
    pattern: "waves",
    rows: AI_REVIEW,
    head: "Public automotive requirements, human-labelled",
    foot: "It finds most real defects and raises many flags people dismiss, so dismissing is one key and sticks. About 60% of its findings recur between runs, so Zyn shows how many runs agreed. Reviewing 46 requirements cost about USD 0.08 with Sonnet.",
  },
];
const ADVANCE = 5;

export function Proof() {
  const [tab, setTab] = useState(0);
  const [dir, setDir] = useState(1);
  const bar = useRef<HTMLSpanElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const clock = useRef(0);
  useRunWhileVisible(root, (dt) => {
    clock.current += dt;
    if (bar.current) bar.current.style.transform = `scaleX(${Math.min(1, clock.current / ADVANCE)})`;
    if (clock.current >= ADVANCE) {
      clock.current = 0;
      setDir(1);
      setTab((t) => (t + 1) % SETS.length);
    }
  });
  const select = (i: number) => {
    clock.current = 0;
    setDir(i >= tab ? 1 : -1);
    setTab(i);
  };
  const onKey = (e: React.KeyboardEvent) => {
    const k = e.key;
    const n = k === "ArrowRight" || k === "ArrowDown" ? tab + 1 : k === "ArrowLeft" || k === "ArrowUp" ? tab - 1 : k === "Home" ? 0 : k === "End" ? SETS.length - 1 : null;
    if (n === null) return;
    e.preventDefault();
    const i = (n + SETS.length) % SETS.length;
    select(i);
    root.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[i]?.focus();
  };
  const set = SETS[tab];

  return (
    <section id="proof" className="section" data-sa="2" aria-labelledby="proof-title">
      <div className="wrap">
        <SectionHead>The proof</SectionHead>
        <div className="proof__head">
          <Headline id="proof-title" plain="We planted mistakes." inked="Here is what code caught." />
          <p className="body">
            We hid mistakes in clean requirements, tests and CAN databases, one at a time, and let Zyn look. No AI involved,
            so the result is the same every run. We publish the misses too. Every number has its dataset, method and limits on
            the{" "}
            <a className="link" href={docHref("benchmarks")}>
              Benchmarks
            </a>{" "}
            page.
          </p>
        </div>

        <div ref={root}>
            <div className="htabs" role="tablist" aria-label="Which results" onKeyDown={onKey}>
              {SETS.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  aria-selected={i === tab}
                  tabIndex={i === tab ? 0 : -1}
                  className="htab"
                  data-active={i === tab || undefined}
                  onClick={() => select(i)}
                >
                  <AnimatePresence>
                    {i === tab && (
                      <motion.span
                        className="htab__progress"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.18, ease: QUART }}
                      >
                        <span ref={bar} />
                      </motion.span>
                    )}
                  </AnimatePresence>
                  <span className="htab__label">{s.label}</span>
                  <span className="htab__count">{s.rows.length} results</span>
                </button>
              ))}
            </div>

          <div className="demo field--sa" data-sa={2}>
            <PatternField pattern={set.pattern} />
            <span className="panel__bar panel__bar--top demo__bar" aria-hidden />
            <span className="panel__bar panel__bar--bottom demo__bar" aria-hidden />
            <div className="demo__sheet">
              <i className="demo__px demo__px--tl" />
              <i className="demo__px demo__px--tr" />
              <i className="demo__px demo__px--bl" />
              <i className="demo__px demo__px--br" />
              {/* Invisible copies of every set, stacked in one cell: the sheet is always as tall as
                  the tallest set, so nothing is cut off and switching tabs never changes its size. */}
              {SETS.map((s) => (
                <div key={s.id} className="ledger ledger--sizer" aria-hidden>
                  <div className="ledger__head">
                    <span>{s.head}</span>
                    <span>Caught</span>
                  </div>
                  <ol className="ledger__rows">
                    {s.rows.map((r) => (
                      <li key={r.mistake} className="ledger__row">
                        <span className="ledger__mistake">
                          {r.mistake}
                          {r.note && <span className="ledger__note">{r.note}</span>}
                        </span>
                        <span className="ledger__bar" />
                        <span className="ledger__n">
                          {r.caught}
                          <span className="ledger__of"> of {r.of}</span>
                        </span>
                      </li>
                    ))}
                  </ol>
                  <p className="ledger__foot">{s.foot}</p>
                </div>
              ))}
              <AnimatePresence initial={false} custom={dir} mode="popLayout">
                <motion.div
                  key={set.id}
                  custom={dir}
                  className="ledger"
                  role="tabpanel"
                  aria-label={set.label}
                  variants={{
                    enter: (d: number) => ({ x: 44 * d, opacity: 0, filter: "blur(2px)" }),
                    rest: { x: 0, opacity: 1, filter: "blur(0px)", transition: { duration: 0.48, ease: HOUSE } },
                    leave: (d: number) => ({ x: -36 * d, opacity: 0, filter: "blur(2px)", transition: { duration: 0.36, ease: HOUSE } }),
                  }}
                  initial="enter"
                  animate="rest"
                  exit="leave"
                >
                  <div className="ledger__head">
                    <span>{set.head}</span>
                    <span>Caught</span>
                  </div>
                  <motion.ol
                    className="ledger__rows"
                    initial="hide"
                    animate="show"
                    variants={{ show: { transition: { delayChildren: 0.1, staggerChildren: 0.065 } } }}
                  >
                    {set.rows.map((r) => (
                      <Row key={r.mistake} row={r} />
                    ))}
                  </motion.ol>
                  <p className="ledger__foot">{set.foot}</p>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const rowV = {
  hide: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: QUART } },
};

function Row({ row }: { row: ProofRow }) {
  const share = row.caught / row.of;
  return (
    <motion.li className="ledger__row" variants={rowV} data-full={row.caught === row.of || undefined}>
      <span className="ledger__mistake">
        {row.mistake}
        {row.note && <span className="ledger__note">{row.note}</span>}
      </span>
      <span className="ledger__bar" aria-hidden>
        <motion.span
          className="ledger__hit"
          variants={{ hide: { scaleX: 0 }, show: { scaleX: share, transition: { duration: 0.55, ease: HOUSE } } }}
        />
      </span>
      <span className="ledger__n">
        {row.caught}
        <span className="ledger__of"> of {row.of}</span>
      </span>
    </motion.li>
  );
}
