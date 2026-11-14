import { Command } from "cmdk";
import { useEffect, useState } from "react";
import { Drawer } from "vaul";
import { SECTIONS, TOOLS } from "../content";
import { DOCS, docHref, splitDoc } from "../docs/docs";
import { goSection, navigate } from "../router";
import { Icon, ZMark } from "../components/ui";
import { CheckerBand, SliderRule } from "../components/bands";
import { Wordmark } from "../components/Wordmark";
import { motion } from "motion/react";
import { useRef } from "react";

type Theme = "system" | "light" | "dark";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem("zyn.site.theme") as Theme) || "system";
    } catch {
      return "system";
    }
  });
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && mq.matches);
      document.documentElement.dataset.theme = dark ? "dark" : "light";
    };
    apply();
    try {
      localStorage.setItem("zyn.site.theme", theme);
    } catch {
      /* private window: the choice lasts for this visit only */
    }
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);
  return [theme, setTheme] as const;
}

const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
const THEME_ICON: Record<Theme, string> = { system: "theme-system", light: "theme-light", dark: "theme-dark" };

export const go = goSection;

export function Nav({ theme, onTheme, onPalette }: { theme: Theme; onTheme: (t: Theme) => void; onPalette: () => void }) {
  const [menu, setMenu] = useState(false);
  return (
    <header className="nav">
      <div className="wrap nav__row">
        <a href={docHref("")} className="brand" aria-label="Zyn home">
          <ZMark size={26} loop />
          <span className="brand__word">Zyn</span>
          <span className="brand__slip">prototype</span>
        </a>
        <nav className="nav__links" aria-label="Sections">
          {SECTIONS.slice(0, 5).map((s) => (
            <a key={s.id} href={`${docHref("")}#${s.id}`} onClick={(e) => (e.preventDefault(), go(s.id))}>
              {s.label}
            </a>
          ))}
        </nav>
        <div className="nav__end">
          <button type="button" className="btn btn--ghost btn--kbd" onClick={onPalette} aria-label="Open the command menu">
            <Icon name="search" size={14} />
            <kbd>Ctrl K</kbd>
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            onClick={() => onTheme(NEXT[theme])}
            aria-label={`Theme: ${theme}. Switch to ${NEXT[theme]}.`}
            title={`Theme: ${theme}`}
          >
            <Icon name={THEME_ICON[theme]} size={16} />
          </button>
          <a className="btn btn--line nav__repo" href={docHref("docs")}>
            Docs
          </a>
          <a className="btn btn--ink" href={`${docHref("")}#contribute`} onClick={(e) => (e.preventDefault(), go("contribute"))}>
            Contribute
          </a>
          <Drawer.Root open={menu} onOpenChange={setMenu} direction="right">
            <Drawer.Trigger className="btn btn--line btn--icon nav__burger" aria-label="Open the menu">
              <span className="burger" aria-hidden>
                <i />
                <i />
                <i />
              </span>
            </Drawer.Trigger>
            <Drawer.Portal>
              <Drawer.Overlay className="drawer__overlay" />
              <Drawer.Content className="drawer" aria-describedby={undefined}>
                <Drawer.Title className="drawer__title">
                  <ZMark size={22} /> Zyn
                </Drawer.Title>
                <nav className="drawer__links" aria-label="Sections">
                  {SECTIONS.map((s) => (
                    <a
                      key={s.id}
                      href={`${docHref("")}#${s.id}`}
                      onClick={(e) => {
                        e.preventDefault();
                        setMenu(false);
                        setTimeout(() => go(s.id), 260);
                      }}
                    >
                      {s.label}
                      <Icon name="chevron-right" size={14} />
                    </a>
                  ))}
                  <a href={docHref("docs")} onClick={() => setMenu(false)}>
                    Docs
                    <Icon name="chevron-right" size={14} />
                  </a>
                </nav>
              </Drawer.Content>
            </Drawer.Portal>
          </Drawer.Root>
        </div>
      </div>
    </header>
  );
}

export function Palette({ open, setOpen, setTheme }: { open: boolean; setOpen: (v: boolean) => void; setTheme: (t: Theme) => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const run = (fn: () => void) => {
    setOpen(false);
    setTimeout(fn, 120);
  };

  return (
    <Command.Dialog open={open} onOpenChange={setOpen} label="Command menu" className="palette" overlayClassName="palette__overlay">
      <Command.Input placeholder="Jump to a section or a docs page, change the theme" className="palette__input" />
      <Command.List className="palette__list">
        <Command.Empty className="palette__empty">Nothing matches. Try "proof" or "sift".</Command.Empty>
        <Command.Group heading="Go to" className="palette__group">
          {SECTIONS.map((s) => (
            <Command.Item key={s.id} onSelect={() => run(() => go(s.id))} className="palette__item">
              <Icon name="next" size={14} />
              {s.label}
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="Tools" className="palette__group">
          {TOOLS.filter((t) => !t.planned).map((t) => (
            <Command.Item key={t.id} onSelect={() => run(() => navigate(docHref(t.id)))} className="palette__item" keywords={[t.text]}>
              <Icon name={t.mark} size={14} />
              {t.name}
              <span className="palette__hint">{t.text}</span>
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="Theme" className="palette__group">
          {(["system", "light", "dark"] as Theme[]).map((t) => (
            <Command.Item key={t} onSelect={() => run(() => setTheme(t))} className="palette__item">
              <Icon name={THEME_ICON[t]} size={14} />
              Use {t} theme
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="Docs" className="palette__group">
          {DOCS.map((d) => (
            <Command.Item key={d.slug} onSelect={() => run(() => navigate(docHref(d.slug)))} className="palette__item" keywords={[d.group, d.inked]}>
              <Icon name="evidence-report" size={14} />
              {d.slug === "docs" ? "All docs" : splitDoc(d.file).title}
              <span className="palette__hint">{d.group}</span>
            </Command.Item>
          ))}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}

export function Footer() {
  const [hover, setHover] = useState<string | null>(null);
  const leave = useRef(0);
  const enter = (k: string) => {
    window.clearTimeout(leave.current);
    setHover(k);
  };
  const out = () => {
    leave.current = window.setTimeout(() => setHover(null), 180);
  };
  return (
    <footer className="footer field field--hero">
      <CheckerBand />
      <div className="wrap footer__cols">
        <div className="footer__lead">
          <p className="footer__tagline">
            Traceable work.
            <br />
            Checked twice.
            <br />
            Decided by a person.
          </p>
          <p className="footer__small">Coming soon. Zyn prototype: public and synthetic data only.</p>
        </div>
        {(["Tools", "Evidence", "Build"] as const).map((g) => (
          <FooterCol
            key={g}
            title={g}
            hover={hover}
            onEnter={enter}
            onLeave={out}
            links={DOCS.filter((d) => FOOTER[g].includes(d.slug)).map((d) => [splitDoc(d.file).title, docHref(d.slug)])}
          />
        ))}
      </div>
      <div className="wrap">
        <SliderRule widths={[32, 40]} gap={0.4888} />
      </div>
      <div className="wrap footer__mark">
        <Wordmark />
      </div>
      <div className="wrap">
        <SliderRule widths={[40, 40]} gap={0.5095} />
      </div>
      <div className="wrap footer__base">
        <span>Zyn. Built to be checked.</span>
        <a href={docHref("docs")} className="link">
          All docs
        </a>
      </div>
      <CheckerBand />
    </footer>
  );
}

const FOOTER = {
  Tools: ["sift", "sift-review", "sift-delta", "anvil", "anvil-review", "assay"],
  Evidence: ["benchmarks", "checks-reference", "research-basis", "how-zyn-decides"],
  Build: ["getting-started", "integrations", "architecture", "roadmap"],
};

function FooterCol({
  title,
  links,
  hover,
  onEnter,
  onLeave,
}: {
  title: string;
  links: string[][];
  hover: string | null;
  onEnter: (k: string) => void;
  onLeave: () => void;
}) {
  return (
    <div className="footer__col">
      <h3>{title}</h3>
      <ul>
        {links.map(([label, href]) => (
          <li key={label}>
            {hover === href && (
              <motion.i layoutId="foot-marker" className="footer__marker" transition={{ duration: 0.09, ease: [0.165, 0.84, 0.44, 1] }} />
            )}
            <a href={href} onPointerEnter={() => onEnter(href)} onPointerLeave={onLeave} onFocus={() => onEnter(href)} onBlur={onLeave}>
              {label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
