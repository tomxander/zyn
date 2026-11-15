import { motion } from "motion/react";
import { useRef } from "react";
import { OUTSIDE, STUDY } from "../content";
import { Headline, SectionHead } from "../components/ui";
import { Panel } from "../components/Panel";
import { HOUSE, QUART, useVisibleClock } from "../components/runtime";

const cubicOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

export function Problem() {
  const ref = useRef<HTMLDivElement>(null);
  const t = useVisibleClock(ref, 3); // seconds of visible time since first seen
  const show = (at: number) => t >= at;
  const stage = (at: number) => ({
    initial: false as const,
    animate: show(at) ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 },
    transition: { duration: 0.18, ease: QUART },
  });
  const count = (n: number) => Math.round(n * cubicOut(t / 1.2));

  return (
    <section id="problem" className="section" data-sa="0" aria-labelledby="problem-title">
      <div className="wrap">
        <SectionHead>The problem</SectionHead>
      </div>
      <div className="wrap split">
        <div className="split__text">
          <Headline id="problem-title" plain="Writing is fast now." inked="Checking still takes days." />
          <p className="body">
            An AI assistant drafts a requirement set in minutes. A supplier sends a revised one on Friday. Someone still has
            to read every line against the spec, and that is where the time goes. In 23 public discussions among embedded,
            test and automotive practitioners, <mark className="hl">14 of 23</mark> named checking AI output as the biggest cost.
          </p>
          <p className="body body--strong">
            The danger isn't slow tools. It's work that is wrong in ways that look right. Zyn doesn't write more. It shows you
            where to look.
          </p>
        </div>

        <Panel sa={0} pattern="waves">
          <motion.div
            ref={ref}
            className="sheet sheet--ink sheet--study"
            initial={false}
            animate={show(0.5) ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.94 }}
            transition={{ duration: 0.45, ease: HOUSE }}
          >
            <motion.div className="sheet__head" {...stage(0.6)}>
              <span>What engineers said</span>
              <span className="sheet__meta">23 discussions</span>
            </motion.div>
            <motion.div className="study__total" {...stage(0.66)}>
              <span className="study__big">{count(14)}</span>
              <span className="study__of-big">of 23</span>
              <span className="study__cap">say checking AI output is the biggest cost</span>
            </motion.div>
            <ol className="study">
              {STUDY.map((s, i) => (
                <motion.li key={s.label} className="study__row" {...stage(0.84 + i * 0.06)}>
                  <span className="study__sq" aria-hidden />
                  <span className="study__label">{s.label}</span>
                  <span className="study__n">
                    {count(s.n)}
                    <span className="study__of"> of 23</span>
                  </span>
                  <span className="study__bar" aria-hidden>
                    <motion.span
                      initial={false}
                      animate={{ scaleX: show(0.9 + i * 0.06) ? s.n / 23 : 0 }}
                      transition={{ duration: 0.5, ease: HOUSE }}
                    />
                  </span>
                </motion.li>
              ))}
            </ol>
            <motion.p className="sheet__foot" {...stage(1.08)}>
              Source: the practitioner study in the Zyn repository.
            </motion.p>
          </motion.div>
        </Panel>
      </div>

      <div className="wrap">
        <div className="outside" aria-labelledby="outside-title">
          <h3 id="outside-title" className="outside__title">What published research adds</h3>
          <ul className="outside__grid">
            {OUTSIDE.map((o) => (
              <li key={o.big} className="outside__cell">
                <p className="outside__big">
                  {o.big} <span className="outside__unit">{o.unit}</span>
                </p>
                <p className="outside__text">{o.text}</p>
                <p className="outside__src">{o.source}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
