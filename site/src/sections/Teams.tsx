import { motion } from "motion/react";
import { useRef, useState } from "react";
import { MODE_ROWS, MODES } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";
import { Panel } from "../components/Panel";
import type { Pattern } from "../components/PatternField";
import { HOUSE, QUART, reduced, useRunWhileVisible, useVisible } from "../components/runtime";

const PATTERNS: Pattern[] = ["bow", "lattice"];
const ADVANCE = 6; // seconds of visible time per mode, until someone picks one

/** Personal mode and team mode: the same install, the same checks, different walls. */
export function Teams() {
  const [mode, setMode] = useState(0);
  const [held, setHeld] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const clock = useRef(0);
  const bar = useRef<HTMLSpanElement>(null);
  useRunWhileVisible(
    root,
    (dt) => {
      clock.current += dt;
      if (bar.current) bar.current.style.transform = `scaleX(${Math.min(1, clock.current / ADVANCE)})`;
      if (clock.current >= ADVANCE) {
        clock.current = 0;
        setMode((m) => (m + 1) % MODES.length);
      }
    },
    !held,
  );
  const pick = (i: number) => {
    setHeld(true);
    setMode(i);
  };
  const onKey = (e: React.KeyboardEvent) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
    e.preventDefault();
    const i = (mode + 1) % MODES.length;
    pick(i);
    root.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[i]?.focus();
  };
  const m = MODES[mode];

  return (
    <section id="teams" className="section" data-sa="0" aria-labelledby="teams-title">
      <div className="wrap">
        <SectionHead>For teams</SectionHead>
      </div>
      <div className="wrap split" ref={root}>
        <div className="split__text">
          <Headline id="teams-title" plain="Try it on your desk." inked="Run it for your team." />
          <p className="body">
            Start on your own laptop in minutes, with no account and no key. When your team is ready, IT runs the same Zyn
            on your own servers or cloud account, behind your company sign-in, with only the models they approve (tested in a container, not yet run at a company).
          </p>
          <div className="seg" role="tablist" aria-label="Which mode" onKeyDown={onKey}>
            {MODES.map((x, i) => (
              <button
                key={x.id}
                type="button"
                role="tab"
                aria-selected={i === mode}
                aria-controls="mode-sheet"
                tabIndex={i === mode ? 0 : -1}
                className="seg__btn"
                onClick={() => pick(i)}
              >
                {i === mode && (
                  <motion.span layoutId="seg-ink" className="seg__ink" transition={{ duration: reduced() ? 0 : 0.32, ease: HOUSE }} />
                )}
                <span className="seg__label">{x.label}</span>
                <span className="seg__note">{x.note}</span>
              </button>
            ))}
            {!held && (
              <span className="seg__progress" aria-hidden>
                <span ref={bar} />
              </span>
            )}
          </div>
          <p className="teams__foot">
            Team mode ships as a container image and a compose file. Each change is built, started and signed in through a trial Keycloak
            automatically; it has not yet run at a company, so try it on a test host first.
          </p>
        </div>

        <Panel sa={0} pattern={PATTERNS[mode]}>
          <div className="sheet sheet--ink sheet--code modes" id="mode-sheet" role="tabpanel" aria-label={m.label}>
            <div className="sheet__head">
              <span className="sheet__method">$</span>
              <span className="modes__cmd">
                {MODES.map((x, i) => (
                  <motion.span
                    key={x.id}
                    initial={false}
                    animate={{ opacity: i === mode ? 1 : 0, y: i === mode ? 0 : i < mode ? -6 : 6 }}
                    transition={{ duration: 0.28, ease: QUART }}
                    aria-hidden={i !== mode}
                  >
                    {x.cmd}
                  </motion.span>
                ))}
              </span>
            </div>
            <dl className="modes__rows">
              {MODE_ROWS.map((r, i) => (
                <div key={r.k} className="modes__row">
                  <dt>{r.k}</dt>
                  <dd>
                    {(["desk", "team"] as const).map((key, j) => (
                      <motion.span
                        key={key}
                        initial={false}
                        animate={{ opacity: j === mode ? 1 : 0, x: j === mode ? 0 : j < mode ? -8 : 8 }}
                        transition={{ duration: 0.3, ease: QUART, delay: reduced() ? 0 : i * 0.035 }}
                        aria-hidden={j !== mode}
                        data-team={key === "team" || undefined}
                      >
                        {r[key]}
                      </motion.span>
                    ))}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="sheet__foot sheet__foot--row">
              <Icon name="passed" size={14} />
              Same checks, same tools, same screen
            </div>
          </div>
        </Panel>
      </div>

      <div className="wrap">
        <Walls />
      </div>
    </section>
  );
}

/** Where team mode runs: everything inside the company's walls, nothing out to Zyn's makers. */
function Walls() {
  const ref = useRef<HTMLDivElement>(null);
  useVisible(ref);
  return (
    <figure className="walls" ref={ref} data-run-surface aria-labelledby="walls-cap">
      <div className="walls__box">
        <span className="walls__label">Your network or your cloud account</span>
        <div className="walls__flow">
          <Node title="Company sign-in" sub="Entra ID, Okta, Keycloak, Ping" />
          <Wire speed={2.2} />
          <Node title="Zyn team server" sub="checks, AI reviewer, screen" core />
          <Wire speed={2.6} />
          <Node title="Audit log" sub="your PostgreSQL, append-only" />
        </div>
        <div className="walls__drop">
          <Wire speed={1.8} down />
          <Node title="Models IT allows" sub="Claude or Ollama today; anything else refused" />
        </div>
      </div>
      <div className="walls__out">
        <span className="walls__cut" aria-hidden>
          <i />
        </span>
        <Node title="Zyn's makers" sub="nothing sent" muted />
      </div>
      <figcaption id="walls-cap" className="walls__cap">
        Zyn sends nothing home: no telemetry, no update checks, no licence calls. Offline mode refuses every cloud call.
      </figcaption>
    </figure>
  );
}

function Node({ title, sub, core, muted }: { title: string; sub: string; core?: boolean; muted?: boolean }) {
  return (
    <div className="wnode" data-core={core || undefined} data-muted={muted || undefined}>
      <span className="wnode__title">{title}</span>
      <span className="wnode__sub">{sub}</span>
    </div>
  );
}

function Wire({ speed, down }: { speed: number; down?: boolean }) {
  return (
    <span className="wline" data-down={down || undefined} aria-hidden>
      <i style={{ animationDuration: `${speed}s` }} />
      <i style={{ animationDuration: `${speed}s`, animationDelay: `${-speed / 2}s` }} />
    </span>
  );
}
