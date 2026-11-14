import { Accordion } from "radix-ui";
import { FAQ, LIMITS, WHY } from "../content";
import { Headline, Icon, Tag } from "../components/ui";

export function Why() {
  return (
    <section id="why" className="section section--table" aria-labelledby="why-title">
      <div className="wrap">
        <Tag>Why Zyn</Tag>
        <Headline id="why-title" plain="Built to be checked," inked="not to be believed." />
        <div className="grid9">
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
