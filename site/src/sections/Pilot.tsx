import { PILOT } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";
import { goSection } from "../router";

/** The measured pilot: how a team finds out whether Zyn helps, on its own work. */
export function Pilot() {
  return (
    <section id="pilot" className="section" aria-labelledby="pilot-title">
      <div className="wrap">
        <SectionHead>Pilot</SectionHead>
        <div className="proof__head">
          <Headline id="pilot-title" plain="Don't take our word." inked="Measure it on your work." />
          <p className="body">
            We don't quote a time saving, because nobody has measured one yet. A pilot measures it with your engineers, on
            your specification, with and without Zyn.
          </p>
        </div>
        <ol className="pilot">
          {PILOT.map((p, i) => (
            <li key={p.title} className="pilot__step">
              <span className="pilot__n" aria-hidden>
                {i + 1}
              </span>
              <h3>{p.title}</h3>
              <p>{p.text}</p>
            </li>
          ))}
        </ol>
        <div className="pilot__cta">
          <button type="button" className="btn btn--ink" onClick={() => goSection("contribute")}>
            Ask for a pilot
            <Icon name="chevron-right" size={12} />
          </button>
          <p className="pilot__note">Leave a note in the form below and pick "Run a pilot on my team's work".</p>
        </div>
      </div>
    </section>
  );
}
