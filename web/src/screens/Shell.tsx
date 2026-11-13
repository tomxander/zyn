// App frame: sidebar (brand, reviewer, runs, start new, theme) and the main column.

import { ZynMark, Command, Monitor, Moon, Plus, Search, Sun, TriangleAlert } from "../components/icons";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useConfig, useRuns } from "../lib/api";
import { markFor } from "../components/ui";
import { useReviewer } from "../lib/reviewer";
import { Button, Tip } from "../components/ui";
import { T_LAYOUT } from "../components/motion";

/** A run's tool mark, from the identity set. */
function toolMark(tool: string) {
  const Mark = markFor(tool);
  return <Mark size={13} aria-hidden />;
}

const MAC = /Mac|iPhone|iPad/.test(navigator.platform);

const fmt = (created: string) => {
  const m = created.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/);
  if (!m) return created;
  const d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};

/** Sidebar line: whether a project knowledge file is added to every model call, and replay. */
function KnowledgeLine({ k, replay }: { k: any; replay: boolean }) {
  const reuse = replay ? "Stored answers are reused when the model, prompt and input match." :
    "Replay is off: every call asks the model.";
  if (k.state === "in_use") {
    return (
      <Tip text={`${k.lines} lines, version ${k.sha}, added to every model call. ${reuse}`}>
        <p className="side-hint">Project knowledge <code>{k.path}</code></p>
      </Tip>
    );
  }
  const why = k.state === "empty"
    ? `Set to ${k.path}, which is missing or empty. Copy knowledge.example.md to start.`
    : "No knowledge_file in config.yaml.";
  return (
    <Tip text={`${why} ${reuse}`}>
      <p className="side-hint">No project knowledge file</p>
    </Tip>
  );
}

export function Shell({ runId, onRun, onNew, onPalette, children }: {
  runId: string | null; onRun: (id: string) => void; onNew: () => void; onPalette: () => void;
  children: ReactNode;
}) {
  const { reviewer, setReviewer, theme, setTheme } = useReviewer();
  const runs = useRuns();
  const cfg = useConfig();
  const [all, setAll] = useState(false);
  // On a phone the run list folds away so the record itself is in the first screen.
  const [runsOpen, setRunsOpen] = useState(false);
  const list = runs.data ?? [];
  const recent = list.slice(0, 12);
  const current = list.find((r) => r.run_id === runId);
  // The open run always stays visible, even when it is older than the recent twelve.
  const shown = all ? list : current && !recent.includes(current) ? [...recent, current] : recent;
  // Only the run list scrolls; keep the open run in view inside it.
  const runsRef = useRef<HTMLElement>(null);
  useEffect(() => {
    runsRef.current?.querySelector<HTMLElement>("[aria-current]")?.scrollIntoView({ block: "nearest" });
  }, [runId, shown.length]);

  return (
    <div className="app">
      <aside className="sidebar" data-runs-open={runsOpen ? "" : undefined}>
        <div className="brand">
          <ZynMark size={22} aria-hidden /><b>ZYN</b><span className="brand-tag">review · prototype</span>
        </div>

        <div className="side-label">Reviewer</div>
        <input className="input" placeholder="Your name" value={reviewer} aria-label="Reviewer name"
          onChange={(e) => setReviewer(e.target.value)} />
        {!reviewer && <p className="side-hint">Required to approve, reject, edit or run a stage.</p>}

        <div className="side-label">
          <span>Runs</span>
          <Button variant="ghost" size="sm" className="runs-toggle" aria-expanded={runsOpen}
            onClick={() => setRunsOpen(!runsOpen)}>{runsOpen ? "Hide" : `Show ${list.length}`}</Button>
          <Tip text="Find a run or an action (Ctrl+K)">
            <Button variant="ghost" size="sm" icon={Search} aria-label="Search" onClick={onPalette} />
          </Tip>
        </div>
        <LayoutGroup>
          <nav className="runs" aria-label="Runs" ref={runsRef}>
            {shown.map((r) => (
              <button key={r.run_id} className="run-item" onClick={() => onRun(r.run_id)}
                aria-current={r.run_id === runId ? "page" : undefined}>
                {r.run_id === runId && <motion.span layoutId="run-bg" className="run-bg" transition={T_LAYOUT} />}
                <span className="run-tool">{toolMark(r.tool)}{r.tool} <span className="quiet">· {fmt(r.created)}</span></span>
                <span className="run-note" title={r.note}>{r.note || r.run_id}</span>
              </button>
            ))}
          </nav>
        </LayoutGroup>
        {list.length > 12 && (
          <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
            {all ? "Show recent only" : `Show all ${list.length} runs`}
          </Button>
        )}
        <Button icon={Plus} onClick={onNew} disabled={!reviewer}
          tip={!reviewer ? "Enter your name as reviewer first" : undefined}>Start new run</Button>

        <div className="side-foot">
          <dl className="hatch-legend" aria-label="What the marks mean">
            <div><dt className="hl-hatch" /><dd>Needs a person</dd></div>
            <div><dt className="hl-cross" /><dd>Conflict or broken</dd></div>
            <div><dt className="hl-dotted" /><dd>Open or advice</dd></div>
            <div><dt className="hl-solid" /><dd>Decided or passed</dd></div>
          </dl>
          {cfg.data && (
            <p className="side-hint">Generator <code>{cfg.data.roles.generator}</code> · AI reviewer{" "}
              <code>{cfg.data.roles.reviewer}</code>{cfg.data.offline && " · offline"}</p>
          )}
          {cfg.data?.knowledge && <KnowledgeLine k={cfg.data.knowledge} replay={cfg.data.replay} />}
          <div className="row">
            {([["system", Monitor], ["light", Sun], ["dark", Moon]] as const).map(([t, Icon]) => (
              <Tip key={t} text={`Theme: ${t}`}>
                <Button variant={theme === t ? "plain" : "ghost"} size="sm" icon={Icon}
                  aria-label={`Theme ${t}`} aria-pressed={theme === t} onClick={() => setTheme(t)} />
              </Tip>
            ))}
            <span className="grow" />
            <Tip text="j k move between cards · a approve · r reject · e edit">
              <span className="side-hint" tabIndex={0}>{MAC ? <span className="kbd"><Command size={10} /> K</span> : <span className="kbd">Ctrl K</span>}</span>
            </Tip>
          </div>
        </div>
      </aside>

      <div id="zyn-live" className="sr-only" aria-live="polite" />
      <main className="main">
        <div className="page">
          <div className="notice"><TriangleAlert aria-hidden />
            <span><b>{cfg.data?.label ?? "Zyn prototype."}</b> Outputs are model-generated and unverified
              until a named reviewer approves them.</span>
          </div>
          <AnimatePresence initial={false}>
            {!reviewer && (
              <motion.p className="small quiet readonly-note" initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                Read-only until you enter your name under Reviewer.
              </motion.p>
            )}
          </AnimatePresence>
          {children}
        </div>
      </main>
    </div>
  );
}
