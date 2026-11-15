import { useEffect, useRef, useState } from "react";
import { PILLARS } from "../content";
import { goSection } from "../router";
import { Icon, reducedMotion } from "../components/ui";
import { HeroFlow } from "./HeroFlow";


/**
 * A rule between words of the headline. An ink block runs along it at 200 px/s, rests 0.1 to
 * 0.7 s, and runs again.
 */
export function Rule({ className = "", car = 32 }: { className?: string; car?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [run, setRun] = useState(0);
  const timer = useRef(0);
  useEffect(() => {
    if (reducedMotion()) return;
    timer.current = window.setTimeout(() => setRun((n) => n + 1), 100 + Math.random() * 600);
    return () => window.clearTimeout(timer.current);
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (el) el.style.setProperty("--road", `${(el.offsetWidth + car) / 200}s`);
  }, [run, car]);
  return (
    <span ref={ref} className={`rule ${className}`} aria-hidden>
      <span className="rule__line" />
      {run > 0 && (
        <i
          key={run}
          className="rule__car"
          style={{ width: car }}
          onAnimationEnd={() => {
            timer.current = window.setTimeout(() => setRun((n) => n + 1), 100 + Math.random() * 600);
          }}
        />
      )}
    </span>
  );
}

export function Hero() {
  return (
    <section className="hero field field--hero" aria-labelledby="hero-title">
      <h1 id="hero-title" className="sr-only">
        AI writes the work. Zyn checks it before you sign.
      </h1>
      <div className="wrap hero__head" aria-hidden={false}>
        <span className="hero__word" aria-hidden>
          AI writes the work.
        </span>
        <Rule className="rule--a" car={40} />
        <p className="hero__desc">
          Suppliers and AI tools now hand you requirements, tests and CAN databases faster than anyone can read them. Zyn
          flags what was changed, invented or weakened, with the source line beside it, so you know where to look
          before you sign.
        </p>
        <Rule className="rule--b" car={28} />
        <span className="hero__break" />
        <Rule className="rule--c" car={20} />
        <span className="hero__ink" aria-hidden>
          Zyn checks it.
          <i className="hero__ink-corner" />
        </span>
        <Rule className="rule--d" car={32} />
        <div className="hero__cta">
          <div className="soon">
            <span className="soon__badge">
              <i aria-hidden />
              Coming soon
            </span>
            <span className="soon__text">In development. Help build it.</span>
            <a className="soon__go" href="#contribute" onClick={(e) => (e.preventDefault(), goSection("contribute"))}>
              Contribute
              <Icon name="chevron-right" size={12} />
            </a>
          </div>
          <p className="hero__aside">
            A hobby project for requirement and test engineers, built in the open and headed for open source.
          </p>
        </div>
        <Rule className="rule--e" car={20} />
      </div>

      <HeroFlow />

      <div className="wrap pillars">
        {PILLARS.map((p) => (
          <div key={p.title} className="pillar">
            <Icon name={p.icon} size={22} />
            <p>
              <strong>{p.title}</strong> {p.text}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
