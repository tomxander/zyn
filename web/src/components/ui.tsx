// Zyn components. Screens build from these; they never style things themselves.
// Each one is listed in docs/design-system.md with when to use it.

import { useAutoAnimate } from "@formkit/auto-animate/react";
import NumberFlow from "@number-flow/react";
import { AlertTriangle, Check, ChevronDown, ChevronRight, CircleAlert, CircleCheck, Info,
  type ZynIconType, Anvil, Assay, Scribe, Sift, Source, ZynMark } from "./icons";
import { AnimatePresence, motion } from "motion/react";
import { Checkbox as RCheckbox, Collapsible, Select as RSelect, Switch as RSwitch, Tabs as RTabs,
  Tooltip } from "radix-ui";
import { createContext, forwardRef, useContext, useEffect, useRef, useState, type ButtonHTMLAttributes,
  type HTMLAttributes, type ReactNode } from "react";
import type { Status, Tone } from "../lib/api";
import { AUTO, enter, fade, item, swap, T_BASE, T_LAYOUT } from "./motion";

/** Tool name to its identity mark (Sift Review and Sift Delta are Sift work, Anvil Review is Anvil work). */
export const TOOL_MARK: Record<string, ZynIconType> = {
  Sift, "Sift Review": Sift, "Sift Delta": Sift, Anvil, "Anvil Review": Anvil, Forge: Anvil, Scribe, Source, Assay,
};
/** A tool's mark; anything without its own (the smoke test) carries the Zyn mark. */
export const markFor = (tool: string): ZynIconType => TOOL_MARK[tool] ?? ZynMark;

export const TONES: Record<Tone, string> = {
  ok: "passed a check, confirmed, approved",
  warn: "needs a person: open, failed check, AI objection",
  info: "edited, needs action, where you are",
  bad: "broken: cannot be used as is",
  muted: "closed with no action: rejected, dismissed",
};
export const STATUS_TONE: Record<Status, Tone> = {
  approved: "ok", edited: "info", proposed: "warn", rejected: "muted",
};
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// ---- labels ------------------------------------------------------------------------------

/** The one status pill on a card. Crossfades when the status changes. */
export function Badge({ text, tone }: { text: string; tone: Tone }) {
  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.span key={text} className={`badge t-${tone}`} variants={swap}
        initial="hidden" animate="show" exit="exit">{cap(text)}</motion.span>
    </AnimatePresence>
  );
}
export const StatusBadge = ({ status }: { status: Status }) =>
  <Badge text={status} tone={STATUS_TONE[status] ?? "muted"} />;

/** A small signal next to content: a count, a recurrence. */
export const Chip = ({ children, tone, icon: Icon }: { children: ReactNode; tone: Tone; icon?: ZynIconType }) =>
  <span className={`chip t-${tone}`}>{Icon && <Icon aria-hidden />}{children}</span>;

/** Pass/fail checks: tick green or ! amber, always with a label. */
export function Checks({ items }: { items: { label: string; ok: boolean }[] }) {
  const [ref] = useAutoAnimate<HTMLDivElement>(AUTO);
  if (!items.length) return null;
  return (
    <div className="chips" ref={ref}>
      {items.map((c) => (
        <Chip key={c.label} tone={c.ok ? "ok" : "warn"} icon={c.ok ? Check : CircleAlert}>{c.label}</Chip>
      ))}
    </div>
  );
}

export const Tag = ({ children }: { children: ReactNode }) => <span className="tag">{children}</span>;

// ---- buttons -----------------------------------------------------------------------------

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "plain" | "ghost"; size?: "sm" | "md"; icon?: ZynIconType; tip?: string;
  wide?: boolean; busy?: boolean;
};
/** One primary per card or tab. Plain for the opposite decision and stage actions. */
export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button(
  { variant = "plain", size = "md", icon: Icon, tip, wide, busy, children, className, disabled, ...rest }, ref) {
  const cls = ["btn", variant === "primary" && "btn-primary", variant === "ghost" && "btn-ghost",
    size === "sm" && "btn-sm", wide && "btn-wide", className].filter(Boolean).join(" ");
  // A disabled button with a tooltip stays focusable (aria-disabled) so the reason can be read,
  // without adding an extra tab stop around it.
  const soft = !!(disabled && tip);
  const b = (
    <button ref={ref} className={cls} disabled={soft ? undefined : disabled || busy}
      aria-disabled={soft || undefined} aria-busy={busy} {...rest}
      onClick={soft ? (e) => e.preventDefault() : rest.onClick}>
      {busy ? <Dots /> : Icon && <Icon aria-hidden />}{children}
    </button>
  );
  return tip ? <Tip text={tip}>{b}</Tip> : b;
});

export function Tip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <Tooltip.Root delayDuration={600}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tooltip" sideOffset={6} asChild>
          <motion.div initial={{ opacity: 0, y: 2 }} animate={{ opacity: 1, y: 0 }} transition={T_BASE}>
            {text}
          </motion.div>
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

// ---- page structure ----------------------------------------------------------------------

/** Split a provenance line ("a.md · converter: plain · sha256 60aa…") into labelled cells. */
function provenance(sub: string): [string, string][] {
  return sub.split(" · ").filter(Boolean).map((part, i) => {
    const kv = part.match(/^([A-Za-z][\w ]{0,24}?):\s+(.+)$/);
    if (kv) return [kv[1], kv[2]];
    const sha = part.match(/^(sha256)\s+(.+)$/i);
    if (sha) return [sha[1], sha[2]];
    return [i === 0 ? "Source" : "", part];
  });
}

/** Top of every run view: the title in condensed capitals over a ruled provenance row.
 *  The tool name is the first cell of that row, never a label above the title. */
export function PageHeader({ kicker, title, sub }: { kicker: string; title: string; sub?: ReactNode }) {
  return (
    <motion.header className="page-head" variants={enter} initial="hidden" animate="show">
      <h1>{title}</h1>
      <dl className="provenance">
        <div className="tool"><dt>Tool</dt><dd>{(() => { const M = markFor(kicker); return <M size={14} aria-hidden />; })()}{kicker}</dd></div>
        {typeof sub === "string"
          ? provenance(sub).map(([k, v], i) => <div key={i}><dt>{k || " "}</dt><dd>{v}</dd></div>)
          : sub && <div><dt>{" "}</dt><dd>{sub}</dd></div>}
      </dl>
    </motion.header>
  );
}

/** A heading inside a tab, above a group of cards or a form. */
export const Section = ({ title, hint }: { title: string; hint?: ReactNode }) => (
  <div className="section"><h2>{title}</h2>{hint && <p>{hint}</p>}</div>
);

/** What is missing and the one thing to do about it. */
export const Empty = ({ icon: Icon = Info, title, body, action }:
  { icon?: ZynIconType; title: string; body: string; action?: ReactNode }) => (
  <motion.div className="empty" variants={enter} initial="hidden" animate="show">
    <Icon aria-hidden /><h3>{title}</h3><p>{body}</p>{action}
  </motion.div>
);

/** Card-level and tab-level messages. bad: code check failed. warn: needs a person.
 *  info: advice. ok: accepted or done. */
const MSG_ICON: Record<Tone, ZynIconType> = { bad: CircleAlert, warn: AlertTriangle, info: Info,
  ok: CircleCheck, muted: Info };
export const Msg = ({ tone, children }: { tone: Tone; children: ReactNode }) => {
  const Icon = MSG_ICON[tone];
  return <div className={`msg t-${tone}`} role={tone === "bad" ? "alert" : undefined}><Icon aria-hidden /><div>{children}</div></div>;
};

// ---- numbers -----------------------------------------------------------------------------

/** A count that rolls when it changes. */
export const Num = ({ value }: { value: number }) => <NumberFlow value={value} className="num" />;

const DECIDED = /^(approved|rejected|confirmed|dismissed)$/i;

/** The counts as one ruled record row. When the counts are decision states, an eleven-step
 *  wedge shows how much of the run is decided (a zone ramp filling from ink). */
export function Stats({ items }: { items: { label: string; value: number; of?: number; tip?: string; aside?: boolean }[] }) {
  const decided = items.filter((s) => DECIDED.test(s.label)).reduce((n, s) => n + s.value, 0);
  const statusRow = items.some((s) => DECIDED.test(s.label)) && items.length >= 3;
  // Items marked aside (such as "requirements with findings") count something else, so
  // they are not part of "decided N of M".
  const total = items.filter((s) => !s.aside).reduce((n, s) => n + s.value, 0);
  const on = total ? Math.round((decided / total) * 11) : 0;
  return (
    <div className="stats">
      {items.map((s) => (
        <div className="stat" key={s.label} title={s.tip}>
          <div className="stat-label">{s.label}</div>
          <div className="stat-value"><NumberFlow value={s.value} />{s.of !== undefined && <small>of {s.of}</small>}</div>
        </div>
      ))}
      {statusRow && total > 0 && (
        <div className="wedge-cell" role="img" aria-label={`${decided} of ${total} decided`}>
          <div className="stat-label">Decided {decided} of {total}</div>
          <div className="wedge">{Array.from({ length: 11 }, (_, i) => <i key={i} data-on={i < on ? "" : undefined} />)}</div>
        </div>
      )}
    </div>
  );
}

// ---- cards -------------------------------------------------------------------------------

/** Long lists skip layout animation: Motion measures every animated card on each update. */
const LayoutOn = createContext(true);
const LAYOUT_LIMIT = 60;

/** The container for a list of cards. Pass how many are shown. */
export function Cards({ count, children, ...rest }: { count: number } & HTMLAttributes<HTMLDivElement>) {
  const ref = useRef<HTMLDivElement>(null);
  // The stack always has a current sheet: the first one, until the reviewer moves.
  useEffect(() => {
    const el = ref.current;
    if (el && !el.querySelector("[data-card][data-current]")) {
      el.querySelector("[data-card]")?.setAttribute("data-current", "");
    }
  });
  return (
    <LayoutOn.Provider value={count <= LAYOUT_LIMIT}>
      <div ref={ref} className="cards" data-stack {...rest}>{children}</div>
    </LayoutOn.Provider>
  );
}

/** An item card. Enters with a short rise, keeps its place when the list filters. It can be
 *  reached with j/k (data-card), and its decision buttons carry data-key for a/r/e. */
export function Card({ index = 0, label, children }: { index?: number; label?: string; children: ReactNode }) {
  const layout = useContext(LayoutOn);
  return (
    <motion.article className="card" data-card tabIndex={-1} aria-label={label}
      layout={layout ? "position" : false} variants={item(index)} initial="hidden"
      animate="show" exit="exit" transition={{ layout: T_LAYOUT }}>
      {children}
    </motion.article>
  );
}

/** First line of every card: ID in mono, a title if any, meta tags, status on the right. */
export function CardHead({ id, title, meta = [], badge }:
  { id: string; title?: string; meta?: (string | null | undefined | false)[]; badge?: ReactNode }) {
  return (
    <div className="card-head">
      <span className="card-id">{id}</span>
      {title && <span className="card-title">{title}</span>}
      <span className="meta">{meta.filter(Boolean).map((m) => <Tag key={String(m)}>{m}</Tag>)}</span>
      {badge && <span className="badge-slot">{badge}</span>}
    </div>
  );
}

export const ItemText = ({ children }: { children: ReactNode }) => <p className="item-text">{children}</p>;
export const Quote = ({ children }: { children: ReactNode }) => <p className="quote">{children}</p>;

/** Word diff: deleted amber with strike, inserted green. */
export function Diff({ ops }: { ops: [string, string][] }) {
  return <>{ops.map(([op, t], i) => (
    <span key={i}>{op === "delete" ? <span className="del">{t}</span> : op === "insert" ? <span className="ins">{t}</span> : t}{" "}</span>
  ))}</>;
}

/** Text with the quoted evidence marked. */
export function Highlight({ text, evidence }: { text: string; evidence?: string }) {
  const i = evidence ? text.toLowerCase().indexOf(evidence.toLowerCase()) : -1;
  if (!evidence || i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<mark>{text.slice(i, i + evidence.length)}</mark>{text.slice(i + evidence.length)}</>;
}

/** A section inside a card that opens smoothly (edit forms, section previews). */
export function Disclosure({ label, children, defaultOpen = false }:
  { label: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="disclosure">
      <Collapsible.Trigger className="disclosure-trigger"><ChevronRight aria-hidden />{label}</Collapsible.Trigger>
      <AnimatePresence initial={false}>
        {open && (
          <Collapsible.Content forceMount asChild>
            <motion.div className="disclosure-body" initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={T_BASE}>
              <div className="stack">{children}</div>
            </motion.div>
          </Collapsible.Content>
        )}
      </AnimatePresence>
    </Collapsible.Root>
  );
}

// ---- tabs --------------------------------------------------------------------------------

/** Numbered when the tabs are stages. The underline slides to the active tab. */
export function Tabs({ tabs, value, onChange, children }: {
  tabs: { value: string; label: string; count?: number }[]; value: string;
  onChange: (v: string) => void; children: ReactNode;
}) {
  return (
    <RTabs.Root value={value} onValueChange={onChange}>
      <RTabs.List className="tabs-list">
        {tabs.map((t) => (
          <RTabs.Trigger key={t.value} value={t.value} className="tab">
            {t.label}{t.count !== undefined && <span className="count"><NumberFlow value={t.count} /></span>}
            {value === t.value && <motion.span layoutId="tab-line" className="tab-line" transition={T_LAYOUT} />}
          </RTabs.Trigger>
        ))}
      </RTabs.List>
      {/* Switching tabs is frequent: a quick fade in, no exit wait. */}
      <motion.div key={value} variants={fade} initial="hidden" animate="show">{children}</motion.div>
    </RTabs.Root>
  );
}

// ---- form controls -----------------------------------------------------------------------

export const Switch = ({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) => (
  <label className="switch">
    <RSwitch.Root className="switch-root" checked={checked} onCheckedChange={onChange}>
      <RSwitch.Thumb className="switch-thumb" />
    </RSwitch.Root>{label}
  </label>
);

export const Checkbox = ({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) => (
  <label className="checkbox">
    <RCheckbox.Root className="checkbox-root" checked={checked} onCheckedChange={(v) => onChange(v === true)}>
      <RCheckbox.Indicator><Check aria-hidden /></RCheckbox.Indicator>
    </RCheckbox.Root>{label}
  </label>
);

export function Select({ value, onChange, options, placeholder, label }: {
  value: string | undefined; onChange: (v: string) => void; placeholder?: string; label?: string;
  options: { value: string; label: string }[];
}) {
  return (
    <RSelect.Root value={value || undefined} onValueChange={onChange}>
      <RSelect.Trigger className="select-trigger" aria-label={label ?? placeholder}>
        <RSelect.Value placeholder={placeholder} /><RSelect.Icon><ChevronDown aria-hidden /></RSelect.Icon>
      </RSelect.Trigger>
      <RSelect.Portal>
        <RSelect.Content className="select-content" position="popper" sideOffset={4}>
          <RSelect.Viewport>
            {options.map((o) => (
              <RSelect.Item key={o.value} value={o.value} className="select-item">
                <RSelect.ItemText>{o.label}</RSelect.ItemText>
              </RSelect.Item>
            ))}
          </RSelect.Viewport>
        </RSelect.Content>
      </RSelect.Portal>
    </RSelect.Root>
  );
}

export const Field = ({ label, children }: { label: string; children: ReactNode }) => (
  <div className="field"><label>{label}</label>{children}</div>
);

/** Toggle chips with counts, for filtering a list. */
export function FilterGroup<T extends string>({ options, selected, onChange, label }: {
  options: { value: T; label: string; count: number }[]; selected: Set<T>; onChange: (s: Set<T>) => void;
  /** Shown before the chips and read out for the group. */
  label?: string;
}) {
  return (
    <div className="filter-group" role="group" aria-label={label}>
      {label && <span className="filter-label" aria-hidden>{label}</span>}
      {options.map((o) => {
        const on = selected.has(o.value);
        return (
          <button key={o.value} className="filter" aria-pressed={on} onClick={() => {
            const next = new Set(selected);
            if (on) next.delete(o.value); else next.add(o.value);
            onChange(next);
          }}>{on && <Check aria-hidden />}{o.label}<span className="count"><NumberFlow value={o.count} /></span></button>
        );
      })}
    </div>
  );
}

// ---- tables and loading ------------------------------------------------------------------

export function Table<R extends Record<string, any>>({ rows, cols, rowKey }: {
  rows: R[]; cols: { key: keyof R & string; label: string; mono?: boolean; render?: (r: R) => ReactNode }[];
  /** A stable key per row (an ID); falls back to the position. */
  rowKey?: (r: R) => string | number;
}) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr>{cols.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={rowKey ? rowKey(r) : i}>{cols.map((c) => <td key={c.key} className={c.mono ? "mono" : undefined}>
              {c.render ? c.render(r) : String(r[c.key] ?? "")}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const Dots = () => <span className="dots" aria-hidden><i /><i /><i /></span>;

export const Skeleton = ({ height }: { height: number }) =>
  <div className="skeleton" style={{ height }} aria-hidden />;

/** Long lists render a screenful at a time. */
export function useProgressive<T>(list: T[], step = 40) {
  const [n, setN] = useState(step);
  const more = list.length > n
    ? <Button variant="ghost" onClick={() => setN(n + step)}>Show {Math.min(step, list.length - n)} more of {list.length - n}</Button>
    : null;
  return { shown: list.slice(0, n), more };
}
