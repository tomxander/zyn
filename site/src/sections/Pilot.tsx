import { PILOT } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";
import { goSection } from "../router";

/** A team trial: how a team finds out whether Zyn helps on its own work, and shares what it learns. */
export function Pilot() {
  return (
    <section id="pilot" className="section" aria-labelledby="pilot-title">
      <div className="wrap">
        <SectionHead>Measure it</SectionHead>
        <div className="proof__head">
          <Headline id="pilot-title" plain="Nobody has measured the time." inked="Help find out." />
          <p className="body">
            Zyn reports what it catches and what it misses, never a time saving, because no one has measured one. If your
            team wants to try it on real work, here is a fair way to run the test and add to what everyone knows.
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
            Offer to run a trial
            <Icon name="chevron-right" size={12} />
          </button>
          <p className="pilot__note">Leave a note in the form below and pick "Run a trial with my team".</p>
        </div>
      </div>
    </section>
  );
}
