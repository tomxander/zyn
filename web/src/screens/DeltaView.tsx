// Sift Delta run: what changed between two revisions, its impact on tests, export, audit log.

import { FileDiff, Save, TriangleAlert } from "../components/icons";
import { AnimatePresence } from "motion/react";
import { useMemo, useState, memo } from "react";
import { useAction, type Decision, type Status, type Tone } from "../lib/api";
import { useReviewer } from "../lib/reviewer";
import { DecisionBar } from "../components/Decision";
import { Badge, Button, Card, CardHead, Diff, Empty, Field, FilterGroup, ItemText, Msg, PageHeader,
  Section, Stats, StatusBadge, Table, Tabs, useProgressive, Cards } from "../components/ui";
import { AuditTab, ExportTab, JobsStrip } from "./common";

const STATE_TONE: Record<string, Tone> = { open: "warn", "needs action": "info", "no action": "muted" };

/** Delta entries carry no decision object; they never need an override reason. */
const plainDecision = (status: Status): Decision =>
  ({ status, block_approve: null, needs_reason: false, reasons: [], earlier: null });

export function DeltaView({ data }: { data: any }) {
  const [tab, setTab] = useState("changes");
  const d = data;
  const m = d.meta;
  return (
    <>
      <PageHeader kicker="Sift Delta" title={`${m.base_file} → ${m.new_file}`}
        sub={`${m.base_run ? `Base run: ${m.base_run} · ` : ""}Unchanged: ${m.unchanged}, not listed · Method: found by code, no model calls`} />
      <JobsStrip jobKey={d.run_id} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "changes", label: "Changes", count: d.entries.length },
        { value: "impact", label: "Impact on tests" },
        { value: "export", label: "Export and score" }, { value: "audit", label: "Audit log" },
      ]}>
        {tab === "changes" && <Changes d={d} />}
        {tab === "impact" && <Impact d={d} />}
        {tab === "export" && <ExportTab runId={d.run_id} label="Export changes (JSON, Excel)"
          disabled={!d.entries.length} scoreKey={d.answer_key_default}
          intro="Exports every change with its decision." after={() => "entries."} />}
        {tab === "audit" && <AuditTab runId={d.run_id} />}
      </Tabs>
    </>
  );
}

// ---- 1. changes --------------------------------------------------------------------------

function Changes({ d }: { d: any }) {
  const entries: any[] = d.entries;
  const labels: Record<string, string> = d.labels;
  const label = (k: string) => labels[k] ?? k;
  const kinds = useMemo(() => [...new Set(entries.map((e) => e.payload.kind as string))].sort(), [entries]);
  const [pick, setPick] = useState<Set<string>>(() => new Set(kinds));
  const shownAll = entries.filter((e) => pick.has(e.payload.kind) || !kinds.includes(e.payload.kind));
  const { shown, more } = useProgressive(shownAll);

  if (!entries.length) {
    return <Empty icon={FileDiff} title="No changes found"
      body={`Every sentence matched between the two revisions (${d.meta.unchanged} unchanged).`} />;
  }
  return (
    <>
      <Stats items={[{ label: "Unchanged", value: d.meta.unchanged },
        ...Object.entries(d.meta.counts as Record<string, number>).map(([k, v]) => ({ label: label(k), value: v }))]} />
      <div className="filters" style={{ marginBottom: "var(--zyn-s5)" }}>
        <FilterGroup label="Show" selected={pick} onChange={setPick}
          options={kinds.map((k) => ({ value: k, label: label(k), count: entries.filter((e) => e.payload.kind === k).length }))} />
      </div>
      <Cards count={shown.length}>
        <AnimatePresence mode="popLayout" initial={false}>
          {shown.map((e, i) => <DeltaCard key={e.item_id} e={e} index={i} />)}
        </AnimatePresence>
      </Cards>
      {!shown.length && <Empty title="Nothing matches these filters" body="Turn a filter back on to see more."
            action={<Button onClick={() => { setPick(new Set(kinds)); }}>Show everything</Button>} />}
      <div className="row" style={{ marginTop: "var(--zyn-s5)" }}>{more}</div>
    </>
  );
}

function DeltaCardInner({ e, index }: { e: any; index: number }) {
  const p = e.payload;
  const who = p.requirement_id || `§${p.new_section || "-"}`;
  const where = (p.kind === "moved" || p.kind === "changed") && `§${p.old_section || "-"} → §${p.new_section || "-"}`;
  return (
    <Card index={index}>
      <CardHead id={who} meta={[e.label, where]}
        badge={<Badge text={e.state} tone={STATE_TONE[e.state] ?? "muted"} />} />
      {p.requirement_text && <p className="small quiet">Approved requirement: {p.requirement_text}</p>}
      <ItemText><Diff ops={p.diff} /></ItemText>
      {e.summary && <p className="small quiet">Code check: {e.summary}
        {p.similarity != null && <> · similarity {p.similarity}</>}</p>}
      {p.note && <p className="small quiet">{p.note}</p>}
      <DecisionBar itemId={e.item_id} decision={plainDecision(e.status)} labels={["Needs action", "No action"]} />
    </Card>
  );
}

// ---- 2. impact on tests ------------------------------------------------------------------

function Impact({ d }: { d: any }) {
  const { canAct, noActReason } = useReviewer();
  const stale = useAction(d.run_id);
  const imp = d.impact;
  const m = d.meta;
  if (!imp) return <Msg tone="info">Impact on tests needs a spec comparison against an approved Sift run.</Msg>;
  const n = imp.stale_total;
  return (
    <div className="stack-lg">
      {!imp.forge_runs.length && <Msg tone="info">No Anvil run has been built from Sift run {m.base_run}.</Msg>}
      <p className="small">Anvil runs built from {m.base_run}: {imp.forge_runs.join(", ") || "none"}. {n} test
        cases rest on requirements whose source changed or was removed.</p>
      {n > 0 && (
        <div className="stack">
          <div><Button variant="primary" icon={TriangleAlert} disabled={!canAct} busy={stale.isPending}
            tip={!canAct ? noActReason : "Recorded per case with this Delta as the reason. Stale cases are left out of Anvil exports."}
            onClick={() => stale.mutate({ name: "mark_stale" })}>Mark {n} test cases stale</Button></div>
          {stale.data && <Msg tone="ok">{stale.data.count} cases marked stale.</Msg>}
        </div>
      )}
      {imp.rows.length > 0 && <Table rows={imp.rows} cols={[
        { key: "requirement_id", label: "Requirement", mono: true }, { key: "kind", label: "Change" },
        { key: "forge_run", label: "Anvil run", mono: true }, { key: "cases", label: "Cases", mono: true },
        { key: "stale", label: "Stale", mono: true },
      ]} />}
      {imp.new_text.length > 0 && (
        <Msg tone="warn">{imp.new_text.length} new sentences in the revision have no requirement and no test yet:{" "}
          {imp.new_text.map((t: string) => t.slice(0, 80)).join("; ")}</Msg>
      )}
      <div>
        <Section title="Update the changed requirements"
          hint="A new version of the Sift requirement, approved here or in the Sift run. Anvil then shows its spec as changed, to propose again." />
        <div className="cards">
          {imp.updates.map((u: any, i: number) => <UpdateCard key={u.entry_id} u={u} runId={d.run_id} index={i} />)}
        </div>
        {!imp.updates.length && <p className="small quiet">No changed requirements to update.</p>}
      </div>
    </div>
  );
}

function UpdateCard({ u, runId, index }: { u: any; runId: string; index: number }) {
  const { canAct, noActReason } = useReviewer();
  const save = useAction(runId);
  const [text, setText] = useState<string>(u.proposal ?? u.current_text);
  const unchanged = text.trim() === u.current_text;
  return (
    <Card index={index}>
      <CardHead id={u.requirement_id} meta={[`v${u.version}`]} badge={<StatusBadge status={u.status} />} />
      <ItemText><Diff ops={u.diff} /></ItemText>
      {u.updated_here ? (
        <>
          <p className="small quiet">Updated from this Delta: {u.current_text}</p>
          {u.status !== "approved" && u.decision && <DecisionBar itemId={u.requirement_item} decision={u.decision} />}
        </>
      ) : (
        <>
          <Field label="New requirement text">
            <textarea className="textarea" value={text} onChange={(ev) => setText(ev.target.value)}
              title="Pre-filled with the new source sentence when the requirement repeated the old one word for word; otherwise edit it yourself." />
          </Field>
          {u.proposal == null && <p className="small quiet">The approved requirement was reworded from its source, so the new wording is yours to write.</p>}
          <div className="card-actions">
            <Button variant="primary" icon={Save} disabled={!canAct || unchanged} busy={save.isPending}
              tip={!canAct ? noActReason : unchanged ? "Change the text first" : undefined}
              onClick={() => save.mutate({ name: "update_requirement", entry_id: u.entry_id,
                requirement_item: u.requirement_item, text: text.trim() })}>Save as new requirement version</Button>
          </div>
        </>
      )}
    </Card>
  );
}

/** Memoised: a decision on one card does not re-render the others. */
const DeltaCard = memo(DeltaCardInner);
