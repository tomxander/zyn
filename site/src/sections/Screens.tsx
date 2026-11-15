import { SCREEN_POINTS } from "../content";
import { Headline, Icon, SectionHead } from "../components/ui";

const BASE = import.meta.env.BASE_URL;

/** Real screenshots of the review screen, in the theme the visitor is using. */
export function Screens() {
  return (
    <section id="screen" className="section section--table" aria-labelledby="screen-title">
      <div className="wrap">
        <SectionHead>The review screen</SectionHead>
        <div className="proof__head">
          <Headline id="screen-title" plain="Every finding shows its evidence." inked="Then it waits for you." />
          <p className="body">
            This is the prototype's review screen: Sift Review on a synthetic instrument cluster requirement set. No mock-up,
            no staged numbers. You can try it yourself, in your browser, on the same data.
          </p>
        </div>
        <figure className="shot">
          <div className="shot__frame">
            <img
              className="shot__img shot__img--light"
              src={`${BASE}img/review-light.png`}
              width={2880}
              height={1800}
              loading="lazy"
              alt="The Zyn review screen in light mode: a finding on a requirement, the quoted words it rests on, who raised it, and Confirm and Dismiss buttons"
            />
            <img
              className="shot__img shot__img--dark"
              src={`${BASE}img/review-dark.png`}
              width={2880}
              height={1800}
              loading="lazy"
              alt="The Zyn review screen in dark mode, showing the same finding"
            />
          </div>
          <figcaption className="shot__cap">Zyn prototype. Synthetic data (ICX-100). Screenshot from 14 November 2026.</figcaption>
        </figure>
        <div className="shot__try">
          <a className="btn btn--ink shot__go" href={`${BASE}demo/`}>
            Try the review screen
            <Icon name="chevron-right" size={12} />
          </a>
          <p className="shot__note">
            The real screen, running in your browser on three recorded runs: confirm and dismiss findings, look through a
            spec revision and generated tests, and download the real exports. Nothing is saved or sent.
          </p>
        </div>
        <ul className="shot__points">
          {SCREEN_POINTS.map((p) => (
            <li key={p.title}>
              <h3>{p.title}</h3>
              <p>{p.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
