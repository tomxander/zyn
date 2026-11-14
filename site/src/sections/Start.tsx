import { useRef, useState } from "react";
import { Headline, Icon, SectionHead } from "../components/ui";
import { PatternField } from "../components/PatternField";
import { reduced, useRunWhileVisible } from "../components/runtime";

/* A scripted terminal (it takes no input): a loop through checking a test suite with Zyn's
   code checks, no key needed. Rows decode left to right behind a scramble front; status lines
   shimmer; the cursor hard-blinks; "Press Enter" flashes on scripted beats. Visible time only. */

type Row = { text: string; kind?: "dim" | "accent" | "status" | "ok" | "logo" | "enter"; delay?: number };
type Screen = { id: string; dur: number; rows: (t: number) => Row[]; press?: boolean; choice?: number };

const CHECKS = ["unknown_signal", "out_of_range", "value_not_traced", "no_check", "unknown_requirement"];

const SCRIPT: Screen[] = [
  {
    id: "intro",
    dur: 2.2,
    press: true,
    rows: () => [
      { text: "", kind: "logo" },
      { text: "Zyn checks AI-made engineering work." },
      { text: "Requirements, tests and CAN databases, from any tool.", kind: "dim" },
      { text: "Code checks run first. No model, no key, no cost.", kind: "dim" },
      { text: "" },
      { text: "Press Enter to start", kind: "enter" },
    ],
  },
  {
    id: "choice",
    dur: 3.8,
    press: true,
    choice: 1,
    rows: () => [
      { text: "What do you want to check?", kind: "accent" },
      { text: "" },
      { text: "  A requirement set from any tool       Sift Review", delay: 0.32 },
      { text: "  Tests from any tool                   Anvil Review", delay: 0.7 },
      { text: "  A new revision of a specification     Sift Delta", delay: 1.08 },
      { text: "" },
      { text: "Up and Down to move, Enter to choose", kind: "dim", delay: 1.32 },
    ],
  },
  {
    id: "map",
    dur: 4.2,
    press: true,
    rows: () => [
      { text: "Found in this folder", kind: "accent" },
      { text: "" },
      { text: "  tests.py                  the test suite", delay: 0.32 },
      { text: "  icx100.dbc                CAN database", delay: 0.7 },
      { text: "  icx100_reqset.csv         requirement set", delay: 1.08 },
      { text: "" },
      { text: "Nothing leaves this machine. Enter to check.", kind: "dim", delay: 1.58 },
    ],
  },
  {
    id: "scan",
    dur: 9.5,
    rows: (t) => [
      { text: "Anvil Review", kind: "accent" },
      { text: "" },
      { text: `Reading tests from their code, not their comments   ${Math.min(17, Math.floor(t / 0.5))}s`, kind: "status" },
      ...CHECKS.slice(0, Math.max(0, Math.floor((t - 1) / 1.4) + 1)).map((c, i) => ({
        text: `  ${c.padEnd(22)} checked`,
        kind: "ok" as const,
        delay: 1 + i * 1.4,
      })),
    ],
  },
  {
    id: "final",
    dur: 10,
    rows: () => [
      { text: "Done. Findings are ready for review.", kind: "accent" },
      { text: "" },
      { text: "Every finding names the check that raised it.", delay: 0.32 },
      { text: "Same input, same result, every run.", delay: 0.7 },
      { text: "Nothing is approved until a named person approves it.", delay: 1.08 },
      { text: "" },
      { text: "Zyn is coming soon. Help build it.", kind: "dim", delay: 1.58 },
    ],
  },
];
const TOTAL = SCRIPT.reduce((a, s) => a + s.dur, 0);
const GLYPHS = [".", "·", "/", "\\", ":"];

function decode(text: string, p: number, frame: number, seed: number) {
  // characters behind the front are final; a 6-char scramble front; blank ahead
  const n = text.length;
  const front = Math.floor(p * (n + 6));
  let out = "";
  for (let i = 0; i < n; i++) {
    if (i < front - 6) out += text[i];
    else if (i < front) out += text[i] === " " ? " " : GLYPHS[(17 * i + 11 * frame + 7 * seed) % 5];
    else out += " ";
  }
  return out;
}

function Shimmer({ text, t }: { text: string; t: number }) {
  const pos = Math.floor(t / 0.08) * 2 - 7;
  return (
    <>
      {text.split("").map((c, i) => {
        const k = i - (pos % (text.length + 14));
        const lit = k >= 0 && k < 7;
        return (
          <span key={i} className={lit ? (k === 0 || k === 6 ? "sh-mid" : "sh-hi") : undefined}>
            {c}
          </span>
        );
      })}
    </>
  );
}

function Terminal() {
  const ref = useRef<HTMLDivElement>(null);
  const [t, setT] = useState(0);
  const acc = useRef(0);
  useRunWhileVisible(ref, (dt) => {
    acc.current = (acc.current + dt) % TOTAL;
    setT(acc.current);
  });
  const still = reduced();
  // which screen, and how far into it
  let start = 0;
  let screen = SCRIPT[SCRIPT.length - 1];
  for (const s of SCRIPT) {
    if (t < start + s.dur) {
      screen = s;
      break;
    }
    start += s.dur;
  }
  const local = still ? 99 : t - start;
  const frame = Math.floor(t / 0.032);
  const pressing = !!screen.press && local > screen.dur - 0.22;
  const rows = screen.rows(local);
  const highlight = screen.choice !== undefined && local > 1.6 ? screen.choice : -1;

  return (
    <div className="term" ref={ref} aria-label="Illustration: a scripted terminal showing how Zyn will check a test suite with code checks only">
      <div className="term__bar">
        <span className="term__dots" aria-hidden>
          <i />
          <i />
          <i />
        </span>
        <span className="term__pill">zyn, preview</span>
        <span className="term__keys">Ctrl K</span>
      </div>
      <div className="term__body" aria-hidden>
        {rows.map((r, i) => {
          if (r.kind === "logo") return <Logo key={`${screen.id}-${i}`} />;
          const startAt = r.delay ?? i * 0.045;
          const p = still ? 1 : Math.min(1, Math.max(0, (local - startAt) / 0.384));
          const choiceRow = screen.choice !== undefined && i === 2 + (highlight >= 0 ? highlight : -9);
          if (r.kind === "enter") {
            return (
              <div key={`${screen.id}-${i}`} className="term__enter" data-press={pressing || undefined}>
                <span>{p >= 1 ? r.text : decode(r.text, p, frame, i)} ↵</span>
              </div>
            );
          }
          return (
            <div key={`${screen.id}-${i}`} className={`term__row term__row--${r.kind ?? "plain"} ${choiceRow ? "is-chosen" : ""}`}>
              {r.kind === "status" && p >= 1 ? <Shimmer text={r.text} t={local} /> : p >= 1 ? r.text : decode(r.text, p, frame, i)}
              {" "}
            </div>
          );
        })}
        <span className="term__cursor" data-on={still || Math.floor(t / 0.45) % 2 === 0 || undefined} />
      </div>
    </div>
  );
}

/** The Z mark as terminal bars: accent runs inside grey rails, each jittering out of phase. */
function Logo() {
  const bars = [
    { rail: 2, bar: 10, period: 0.72 },
    { rail: 7, bar: 3, period: 0.88 },
    { rail: 4, bar: 3, period: 0.78 },
    { rail: 2, bar: 10, period: 0.68 },
  ];
  return (
    <div className="term__logo">
      {bars.map((b, i) => (
        <div key={i} className="term__logo-row">
          <span className="term__rail">{"—".repeat(b.rail)}</span>
          <span className="term__bars" style={{ animationDuration: `${b.period * 4}s`, animationDirection: i % 2 ? "reverse" : "normal" }}>
            {"█".repeat(b.bar)}
          </span>
          <span className="term__rail">{"—".repeat(14 - b.rail - b.bar)}</span>
        </div>
      ))}
    </div>
  );
}

const AREAS = [
  "Run a pilot on my team's work",
  "Try it early as an engineer",
  "Review the answer key",
  "Checks and rules",
  "Model connectors",
  "Requirement tools and test benches",
  "Something else",
];
const ENDPOINT = "/api/zyn-contribute";

type Status = { kind: "idle" | "sending" | "sent" | "error"; note?: string };

function ContributeForm() {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = Object.fromEntries(f.entries());
    setStatus({ kind: "sending" });
    try {
      const res = await fetch(ENDPOINT, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const out = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      if (res.ok && out.ok) setStatus({ kind: "sent" });
      else setStatus({ kind: "error", note: out.error ?? "Your message could not be sent. Try again in a minute." });
    } catch {
      setStatus({ kind: "error", note: "Your message could not be sent. Check your connection and try again." });
    }
  };
  if (status.kind === "sent") {
    return (
      <div className="cform cform--done" role="status">
        <Icon name="passed" size={22} />
        <p className="cform__done-title">Thank you. Your note is in.</p>
        <p className="cform__done-text">We read every one and reply to the address you gave.</p>
      </div>
    );
  }
  const busy = status.kind === "sending";
  return (
    <form className="cform" onSubmit={submit} noValidate={false}>
      <div className="cform__row">
        <label className="cfield">
          <span>Name</span>
          <input name="name" required maxLength={80} autoComplete="name" />
        </label>
        <label className="cfield">
          <span>Email</span>
          <input name="email" type="email" required maxLength={120} autoComplete="email" />
        </label>
      </div>
      <label className="cfield">
        <span>Where you would like to help</span>
        <select name="area" defaultValue={AREAS[0]}>
          {AREAS.map((a) => (
            <option key={a}>{a}</option>
          ))}
        </select>
      </label>
      <label className="cfield">
        <span>What you would bring</span>
        <textarea name="message" required minLength={10} maxLength={2000} rows={4} placeholder="Your background, and the part of Zyn you would like to work on." />
      </label>
      <label className="cform__trap" aria-hidden>
        Leave this empty
        <input name="website" tabIndex={-1} autoComplete="off" />
      </label>
      <div className="cform__foot">
        <button type="submit" className="btn btn--ink cform__send" disabled={busy}>
          {busy ? "Sending..." : "Send"}
        </button>
        <p className="cform__note" role={status.kind === "error" ? "alert" : undefined}>
          {status.kind === "error" ? status.note : "Used only to reply to you about contributing. Nothing is published."}
        </p>
      </div>
    </form>
  );
}

export function Contribute() {
  return (
    <section id="contribute" className="section start" data-sa="4" aria-labelledby="contribute-title">
      <div className="wrap">
        <SectionHead>Contribute</SectionHead>
      </div>
      <div className="wrap start__grid">
        <Terminal />
        <div className="start__panel field--sa" data-sa={4}>
          <PatternField pattern="fan" />
          <span className="panel__bar panel__bar--top" aria-hidden />
          <span className="panel__bar panel__bar--bottom" aria-hidden />
          <div className="start__copy">
            <Headline id="contribute-title" plain="Zyn is coming soon." inked="Help build it." />
            <p className="body">
              Requirement or test engineer? Try it early on sample data and tell us what would make it daily work. Know
              requirements, CAN or test benches well? Review the answer key, so every score stops saying "AI-reviewed". Build
              checks, model connectors or tool round trips? The roadmap is open. Leading a team? Ask for a pilot: we measure
              reviewer minutes with and without Zyn on your own work, and the report says so if there is no gain.
            </p>
            <ContributeForm />
          </div>
        </div>
      </div>
    </section>
  );
}
