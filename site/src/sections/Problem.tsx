import { motion } from "motion/react";
import { useRef } from "react";
import { STUDY } from "../content";
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
            AI can write a requirement set or a test suite in minutes. Checking it is where teams give up. In a public study of
            23 discussions among embedded, test and automotive practitioners, <mark className="hl">14 of 23</mark> named inspecting and correcting AI output as the
            biggest cost.
          </p>
          <p className="body body--strong">
            Engineers don't reject AI tools for being slow. They reject them for being wrong in ways that look right. So Zyn
            doesn't try to generate more. It makes the output checkable.
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
    </section>
  );
}
