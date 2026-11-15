import { NOT_BUILDING, ROAD } from "../content";
import { Headline, SectionHead } from "../components/ui";
import { goSection } from "../router";

/** What is done, what is next, and what Zyn will deliberately never build. */
export function Roadmap() {
  return (
    <section id="roadmap" className="section section--table" aria-labelledby="roadmap-title">
      <div className="wrap">
        <SectionHead>Roadmap</SectionHead>
        <div className="proof__head">
          <Headline id="roadmap-title" plain="What comes next," inked="and what we won't build." />
          <p className="body">
            The order comes from what engineers asked for in public discussions, and from what it takes to run Zyn on
            your own machines. Every item here is open to{" "}
            <a className="link" href="#contribute" onClick={(e) => (e.preventDefault(), goSection("contribute"))}>
              contributors
            </a>
            .
          </p>
        </div>

        <div className="road">
          {ROAD.map((col) => (
            <div key={col.status} className="road__col" data-status={col.status.toLowerCase()}>
              <h3 className="road__head">
                <span className="road__mark" aria-hidden />
                {col.status}
                <span className="road__count">{col.items.length}</span>
              </h3>
              <ol className="road__list">
                {col.items.map((it) => (
                  <li key={it.title} className="road__item">
                    <h4>{it.title}</h4>
                    <p>{it.text}</p>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>

        <div className="never">
          <div className="never__text">
            <h3 className="h3">Not building</h3>
            <p className="body">
              The research found no firsthand demand or working deployment for these, and each would ask a model to make a
              decision that belongs to an engineer.
            </p>
          </div>
          <ul className="never__list">
            {NOT_BUILDING.map((n) => (
              <li key={n}>
                <span className="never__x" aria-hidden />
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
