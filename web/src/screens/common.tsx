// Tabs every run view shares: Export (and score) and Audit log.

import { Download, FileCheck, FileDown, Target } from "../components/icons";
import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { downloadUrl, useAction, useAudit } from "../lib/api";
import { useReviewer } from "../lib/reviewer";
import { Loading } from "../components/Loader";
import { Button, Field, Msg, Section, Stats, Table } from "../components/ui";
import { enter } from "../components/motion";

export function ExportTab({ runId, intro, label, disabled, scoreKey, after }: {
  runId: string; intro: ReactNode; label: string; disabled?: boolean;
  /** Default answer key path; omit to hide scoring. */
  scoreKey?: string; after?: (res: any) => ReactNode;
}) {
  const { reviewer } = useReviewer();
  const exp = useAction(runId);
  const score = useAction(runId);
  const ev = useAction(runId);
  const [key, setKey] = useState(scoreKey ?? "");
  const res = exp.data;
  return (
    <div className="stack-lg">
      <p className="small">{intro}</p>
      <div className="row">
        <Button variant="primary" icon={FileDown} disabled={!reviewer || disabled} busy={exp.isPending}
          tip={!reviewer ? "Enter your name as reviewer first" : undefined}
          onClick={() => exp.mutate({ name: "export" })}>{label}</Button>
      </div>
      <AnimatePresence>
        {res && (
          <motion.div className="stack" variants={enter} initial="hidden" animate="show">
            <Msg tone="ok">Exported <b>{res.count}</b>{after ? <> {after(res)}</> : "."}</Msg>
            <div className="row">
              {Object.entries(res.files as Record<string, string>).map(([kind, path]) => (
                <a key={kind} className="btn" href={downloadUrl(path)} download><Download aria-hidden />{kind.toUpperCase()}</a>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <Section title="Evidence report"
        hint="One verdict per item (pass, fail, warn, skipped, broken) with the evidence and who decided, as HTML (prints to PDF) and JUnit XML, plus the run's audit log as a hash chain." />
      <div className="row">
        <Button icon={FileCheck} disabled={!reviewer} busy={ev.isPending}
          tip={!reviewer ? "Enter your name as reviewer first" : undefined}
          onClick={() => ev.mutate({ name: "evidence" })}>Write evidence report</Button>
      </div>
      {ev.data && (
        <motion.div className="stack" variants={enter} initial="hidden" animate="show">
          <Msg tone="ok">Evidence for <b>{ev.data.count}</b> items: {(["pass", "fail", "warn", "skipped", "broken"] as const)
            .map((k) => `${ev.data.counts[k]} ${k}`).join(", ")}. Audit chain head <code>{String(ev.data.chain_head).slice(0, 16)}</code>.</Msg>
          <div className="row">
            {Object.entries(ev.data.files as Record<string, string>).map(([kind, path]) => (
              <a key={kind} className="btn" href={downloadUrl(path)} download><Download aria-hidden />{kind.toUpperCase()}</a>
            ))}
          </div>
        </motion.div>
      )}
      {scoreKey !== undefined && (
        <>
          <Section title="Score against an answer key"
            hint="Scores count findings before human review. The answer key is author-made and AI-reviewed, not engineer-reviewed." />
          <div className="row">
            <div className="grow"><Field label="Answer key (JSON)"><input className="input" value={key} onChange={(e) => setKey(e.target.value)} /></Field></div>
            <Button icon={Target} disabled={!key} busy={score.isPending} onClick={() => score.mutate({ name: "score", key_path: key })}>Score</Button>
          </div>
          {score.data && (
            <motion.div className="stack" variants={enter} initial="hidden" animate="show">
              {score.data.rows.map((s: any) => (
                <Msg key={s.label} tone="info">
                  <b>{s.label}:</b> {s.found} of {s.required_flags ?? s.expected} expected found
                  {s.flags_not_in_key !== undefined && <> · {s.flags_not_in_key} not in the key · {s.requirements_with_findings} of {s.requirements} requirements with findings</>}
                  {s.missed?.length > 0 && <div className="small quiet">Missed: {s.missed.map((m: any) => typeof m === "string" ? m : `${m.kind} ${m.what ?? ""}`).join(", ")}</div>}
                </Msg>
              ))}
            </motion.div>
          )}
        </>
      )}
    </div>
  );
}

export function AuditTab({ runId }: { runId: string }) {
  const q = useAudit(runId);
  if (!q.data) return <Loading label="Reading the audit log" pattern="wave" />;
  const m = q.data.metrics;
  const mc = m.model;
  const events = q.data.events as any[];
  return (
    <div className="stack-lg">
      <Section title="Effort and cost" hint="From the audit log. Elapsed times include idle time." />
      <Stats items={[
        { label: "Model calls", value: mc.calls, tip: `${mc.schema_retries} schema retries, ${mc.failed_calls} failed, ${mc.blocked_offline} blocked offline` },
        { label: "Answers reused", value: mc.replayed ?? 0, tip: "Same model, prompt and input as an earlier call: the stored answer was used, with no model call, tokens or cost" },
        { label: "Tokens in", value: mc.tokens_in },
        { label: "Tokens out", value: mc.tokens_out },
        { label: "Model time (s)", value: mc.model_seconds },
      ]} />
      <p className="small quiet">Model cost USD {mc.cost_usd.toFixed(2)}{mc.cost_complete ? "" : " +? (a profile has no price)"}</p>
      {(q.data.knowledge as any[]).map((k) => (
        <p key={k.sha} className="small quiet">Project knowledge <code>{k.path}</code> version {k.sha} ({k.lines} lines) in {k.calls} of {k.of_calls} model answers</p>
      ))}
      {Object.entries(m.review as Record<string, any>).map(([kind, r]) => (
        <p key={kind} className="small quiet">{kind.replace(/_/g, " ")}: {r.decided} of {r.items} decided · {r.edited_items} edited ·
          median {r.median_minutes_to_first_decision ?? "-"} min to first decision{r.carried_over ? ` · ${r.carried_over} carried over` : ""}</p>
      ))}
      {m.agreement?.ai_reviewer_on_requirements && (() => {
        const a = m.agreement.ai_reviewer_on_requirements;
        return <p className="small quiet">AI reviewer vs people: objections upheld {a.objection_upheld}, overruled {a.objection_overruled} · accepts confirmed {a.accept_confirmed}, overruled {a.accept_overruled} · undecided {a.undecided}</p>;
      })()}
      <div className="row">
        <a className="btn" href={`data:application/json,${encodeURIComponent(JSON.stringify(events, null, 2))}`}
          download={`audit-${runId}.json`}><Download aria-hidden />Download audit log (JSON)</a>
        <span className="small quiet">{events.length} events</span>
      </div>
      <Table rows={events.slice().reverse().slice(0, 300)} rowKey={(e) => e.event_id} cols={[
        { key: "event_id", label: "#", mono: true }, { key: "ts", label: "Time", mono: true,
          render: (e) => String(e.ts).slice(11, 19) },
        { key: "actor", label: "Actor" }, { key: "action", label: "Action" },
        { key: "object_id", label: "Object", mono: true, render: (e) => (e.object_id ?? "").split("@")[0] },
        { key: "tokens_in", label: "Tokens", mono: true, render: (e) => e.tokens_in ? `${e.tokens_in} / ${e.tokens_out}` : "" },
        { key: "latency_ms", label: "ms", mono: true, render: (e) => e.latency_ms ?? "" },
      ]} />
      {events.length > 300 && <p className="small quiet">Showing the latest 300. The download has all {events.length}.</p>}
    </div>
  );
}

/** Running stages for this run, shown above the tabs. */
export { JobsStrip } from "./JobsStrip";
