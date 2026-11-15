import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Icon, ZMark } from "./ui";
import { HOUSE, QUART, reduced } from "./runtime";

// Bump the version when the note's wording changes, so everyone sees the new one once.
const KEY = "zyn.site.note.v1";

const accepted = () => {
  try {
    return localStorage.getItem(KEY) === "accepted";
  } catch {
    return false;
  }
};

/** A short personal note shown before the site opens, until the visitor accepts it.
 *  Accepting is remembered in this browser, so a returning visitor goes straight in. */
export function Disclaimer() {
  const [open, setOpen] = useState(() => !accepted());
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const root = document.documentElement;
    // Everything behind the note is out of reach of keyboard and screen reader until it closes.
    const behind = Array.from(document.querySelectorAll("main, header, footer, nav, .skip"));
    root.style.overflow = "hidden";
    behind.forEach((el) => el.setAttribute("inert", ""));
    button.current?.focus({ preventScroll: true });
    return () => {
      root.style.overflow = "";
      behind.forEach((el) => el.removeAttribute("inert"));
    };
  }, [open]);

  const accept = () => {
    try {
      localStorage.setItem(KEY, "accepted");
    } catch {
      /* private mode: the note simply shows again next visit */
    }
    setOpen(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="note"
          role="dialog"
          aria-modal="true"
          aria-labelledby="note-title"
          aria-describedby="note-body"
          initial={false}
          exit={{ opacity: 0, transition: { duration: reduced() ? 0 : 0.45, ease: QUART } }}
        >
          <motion.div
            className="note__card"
            initial={reduced() ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0, transition: { duration: 0.5, ease: HOUSE } }}
          >
            <div className="note__head">
              <ZMark size={28} loop />
              <span className="note__tag">A note before you go in</span>
            </div>
            <h1 id="note-title" className="note__title">
              Zyn is a hobby project.
            </h1>
            <div id="note-body" className="note__body">
              <p>
                I build Zyn in my own time, for myself. I wanted to see how far one idea can go: that work written by AI is
                only useful once it can be checked, and that a person should make every final call.
              </p>
              <p>
                It is how I learn. I tinker, test ideas against public data, and write down what works and what doesn't. Nothing
                here is for sale, and I don't plan to make money from it.
              </p>
              <p>
                When it is ready, I will open source it, and I want it to grow into a community project: engineers deciding what
                it checks, adding the checks they need, and keeping its benchmarks honest. If that sounds like you, there is a
                form at the end of the page.
              </p>
              <p>
                Zyn is not affiliated with any employer, client or company. No company's documents or data were used; everything
                you will see runs on public and synthetic data.
              </p>
              <p className="note__small">
                It is a prototype, not a finished product, a qualified tool or professional advice. Read it with that in mind.
              </p>
            </div>
            <div className="note__foot">
              <p className="note__sign">Tom</p>
              <button ref={button} type="button" className="btn btn--ink note__go" onClick={accept}>
                I understand. Enter the site
                <Icon name="chevron-right" size={12} />
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
