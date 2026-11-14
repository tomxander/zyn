import { Accordion } from "radix-ui";
import { FAQ, FITS, LIMITS, WHEN, WHY } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";

/** Daily work: when to reach for Zyn, how it fits the tools a team already has, and where it stops. */
export function Work() {
  return (
    <section id="work" className="section" aria-labelledby="work-title">
      <div className="wrap">
        <SectionHead>Daily work</SectionHead>
        <Headline id="work-title" plain="Built to be checked," inked="not to be believed." />

        <div className="split split--even work">
          <div>
            <h3 className="h3">Use it when</h3>
            <ol className="when">
              {WHEN.map((w) => (
                <li key={w.who} className="when__item">
                  <span className="when__who">{w.who}.</span>
                  <span className="when__then">{w.then}</span>
                </li>
              ))}
            </ol>
          </div>
          <div>
            <h3 className="h3">Fits around your tools</h3>
            <table className="fits">
              <thead>
                <tr>
                  <th scope="col">You use</th>
                  <th scope="col">Zyn gives you</th>
                </tr>
              </thead>
              <tbody>
                {FITS.map((f) => (
                  <tr key={f.use}>
                    <th scope="row">{f.use}</th>
                    <td>{f.gets}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid9 grid9--six">
          {WHY.map((w) => (
            <div key={w.title} className="grid9__cell">
              <h3>{w.title}</h3>
              <p>{w.text}</p>
            </div>
          ))}
        </div>

        <div className="split split--even honest">
          <div>
            <h3 className="h3">Where Zyn stops</h3>
            <p className="body">A checker that oversells itself is worthless, so here is where Zyn stops.</p>
            <ul className="limits">
              {LIMITS.map((l) => (
                <li key={l}>
                  <span className="limits__mark" aria-hidden />
                  {l}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="h3">Questions people ask</h3>
            <Accordion.Root type="single" collapsible className="faq">
              {FAQ.map((f, i) => (
                <Accordion.Item key={f.q} value={`q${i}`} className="faq__item">
                  <Accordion.Header asChild>
                    <h4>
                      <Accordion.Trigger className="faq__trigger">
                        {f.q}
                        <Icon name="chevron-down" size={14} className="faq__chev" />
                      </Accordion.Trigger>
                    </h4>
                  </Accordion.Header>
                  <Accordion.Content className="faq__content">
                    <p>{f.a}</p>
                  </Accordion.Content>
                </Accordion.Item>
              ))}
            </Accordion.Root>
          </div>
        </div>
      </div>
    </section>
  );
}
