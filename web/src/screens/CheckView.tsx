// Sift Review run: findings on an imported requirement set, requirements table, export and
// score, audit log.

import { Layers, ListChecks, Repeat, Sparkles } from "../components/icons";
import { AnimatePresence } from "motion/react";
import { useMemo, useState, memo } from "react";
import { toast } from "sonner";
import { useAction, type Decision, type Tone } from "../lib/api";
import { useStartStage } from "../lib/jobs";
import { useReviewer } from "../lib/reviewer";
import { DecisionBar } from "../components/Decision";
import { Badge, Button, Card, Disclosure, CardHead, Chip, Empty, Field, FilterGroup, Highlight, ItemText, Msg,
  PageHeader, Select, Stats, Switch, Table, Tabs, useProgressive, Cards } from "../components/ui";
import { AuditTab, ExportTab, JobsStrip } from "./common";

type State = "open" | "confirmed" | "dismissed";
type Source = "code" | "ai";
const STATES: State[] = ["open", "confirmed", "dismissed"];
const STATE_TONE: Record<State, Tone> = { open: "warn", confirmed: "ok", dismissed: "muted" };
const SOURCES: { value: Source; label: string }[] = [
  { value: "code", label: "Code check" }, { value: "ai", label: "AI reviewer" }];
const NO_REASON = "none";
const cap = (s: string) => s[0].toUpperCase() + s.slice(1);

export function CheckView({ data }: { data: any }) {
  const [tab, setTab] = useState("findings");
  const d = data;
  const m = d.meta;
  const findings: any[] = d.findings;
  const openN = findings.filter((f) => f.state === "open").length;
  return (
    <>
      <PageHeader kicker={d.tool ?? "Sift Review"} title={m.filename}
        sub={`${m.count} ${m.kind === "tests" ? "tests" : "requirements"} · ${m.source_format} · columns used: ${Object.entries(m.columns_used as Record<string, string>)
          .map(([k, v]) => `${k} = ${v}`).join(", ")} · sha256 ${m.sha256.slice(0, 16)}…`
          + (m.rules ? ` · rule profile ${m.rules.name} (${m.rules.checks.length} checks${m.rules.custom_checks?.length ? `, ${m.rules.custom_checks.length} custom` : ""})` : "")} />
      <JobsStrip jobKey={d.run_id} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "findings", label: `Findings (${openN} open of ${findings.length})` },
        { value: "req", label: d.item_label ?? "Requirements", count: d.requirements.length },
        { value: "export", label: "Export and score" }, { value: "audit", label: "Audit log" },
      ]}>
        {tab === "findings" && <Findings d={d} />}
        {tab === "req" && <Requirements d={d} />}
        {tab === "export" && <ExportTab runId={d.run_id} label={d.meta.kind === "tests" ? "Export findings (JSON, Excel, checklist)" : "Export findings (JSON, Excel, ReqIF)"}
          disabled={!findings.length} scoreKey={d.answer_key_default}
          intro={d.meta.kind === "tests" ? "Exports every finding with its status. Open findings are marked unreviewed. The checklist file rates each test case check FC, LC, PC or NO from the code checks, in the layout the Automotive Engineering Suite uses; checks code cannot decide are marked NA with the reason, never rated, and ratings with undecided findings are marked provisional." : "Exports every finding with its status. Open findings are marked unreviewed. The ReqIF file adds a Zyn review and a Zyn findings attribute to each requirement; when the set came in as ReqIF it is the original file with those two added, ready to import back as an update."}
          after={() => "findings."} />}
        {tab === "audit" && <AuditTab runId={d.run_id} />}
      </Tabs>
    </>
  );
}

/** Excluded values are stored, so categories that appear later start switched on. */
function useHidden<T extends string>(all: T[]) {
  const [hidden, setHidden] = useState<Set<T>>(() => new Set());
  const selected = useMemo(() => new Set(all.filter((v) => !hidden.has(v))), [all, hidden]);
  const onChange = (s: Set<T>) => setHidden(new Set(all.filter((v) => !s.has(v))));
  return { selected, onChange };
}

function Findings({ d }: { d: any }) {
  const { canAct, noActReason } = useReviewer();
  const start = useStartStage(d.run_id);
  const carry = useAction(d.run_id);
  const ai = d.ai;
  const findings: any[] = d.findings;
  const left = ai.batches_left + ai.conflicts_left;
  const multi = ai.passes > 1;
  const [want, setWant] = useState(String(Math.max(3, ai.passes)));
  const more = Number(want) - ai.passes;

  const cats = useMemo(() => [...new Set(findings.map((f) => f.payload.category as string))].sort(), [findings]);
  const pickCat = useHidden(cats);
  const pickSrc = useHidden(SOURCES.map((s) => s.value));
  const pickState = useHidden(STATES);
  const [onlyStable, setOnlyStable] = useState(false);

  const shownAll = findings.filter((f) => pickCat.selected.has(f.payload.category)
    && pickSrc.selected.has(f.payload.source) && pickState.selected.has(f.state)
    && !(multi && onlyStable && f.stability && f.stability.seen < f.stability.passes));
  const { shown, more: moreBtn } = useProgressive(shownAll);
  const count = (fn: (f: any) => boolean) => findings.filter(fn).length;

  return (
    <>
      {d.meta.coverage && (d.meta.coverage.requirements > 0 ? (
        <Msg tone={d.meta.coverage.untested.length ? "warn" : "ok"}>
          {d.meta.coverage.tested} of {d.meta.coverage.requirements} requirements are referenced by a test (code check)
          {d.meta.coverage.untested.length > 0 && <>. No test refers to: {d.meta.coverage.untested.join(", ")}</>}
        </Msg>
      ) : (
        <Msg tone="warn">No requirement set given, so code did not check which requirements the tests cover.</Msg>
      ))}
      {d.meta.coverage?.no_signal?.length > 0 && (
        <Msg tone="warn">
          {d.meta.coverage.no_signal.length} {d.meta.coverage.no_signal.length === 1 ? "test names" : "tests name"} no signal from {d.meta.dbc}, so code could not check {d.meta.coverage.no_signal.length === 1 ? "its" : "their"} values. Reported as skipped, not passed: {d.meta.coverage.no_signal.join(", ")}
        </Msg>
      )}
      {d.meta.coverage?.boundaries?.length > 0 && (
        <Msg tone="warn">
          {d.meta.coverage.boundaries.length} input {d.meta.coverage.boundaries.length === 1 ? "signal is" : "signals are"} never set at some of their DBC limits (code check): {d.meta.coverage.boundaries.map((b: any) => `${b.signal} (no ${b.missing.join(", no ")}; range ${b.minimum} to ${b.maximum})`).join("; ")}
        </Msg>
      )}
      {d.meta.source && (
        <p className="small quiet">Checked against the source {d.meta.source.filename} (sha256 {String(d.meta.source.sha256).slice(0, 12)}): each requirement is matched to a source sentence by code.</p>
      )}
      {d.ai_available !== false && <div className="toolbar">
        <Button variant={left ? "primary" : "plain"} icon={Sparkles} disabled={!canAct || !left}
          tip={!canAct ? noActReason
            : "Each batch checks up to 15 requirements on their own; the conflict pass reads the whole set for contradictions."}
          onClick={() => start("ai_review")}>
          Run AI review ({ai.batches_left} of {ai.batches} batches and {ai.conflicts_left} of {ai.conflicts} set-wide conflict passes left)</Button>
        {d.carry_over > 0 && <Button icon={Repeat} disabled={!canAct} busy={carry.isPending}
          tip={canAct ? "Findings on unchanged text that a person already confirmed or dismissed in an earlier run." : noActReason}
          onClick={() => carry.mutate({ name: "carry_over" },
            { onSuccess: (r) => toast.success(`Applied ${r.count} earlier decisions`) })}>
          Apply {d.carry_over} earlier decisions on identical findings</Button>}
      </div>}
      {d.ai_available !== false && ai.first_pass_done && (
        <div className="toolbar">
          <Field label="AI passes in total">
            <Select value={want} onChange={setWant} label="AI passes in total"
              options={[2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))} />
          </Field>
          {more > 0 && <Button icon={Layers} disabled={!canAct}
            tip={canAct ? "Shows which AI findings recur when the same review is repeated. A finding seen once is weaker evidence than one seen every time. Each extra pass costs about the same as the first." : noActReason}
            onClick={() => start("stability", { passes: Number(want) })}>
            Stability check: run {more} more AI {more === 1 ? "pass" : "passes"}</Button>}
        </div>
      )}
      {!findings.length ? (
        <Empty icon={ListChecks} title="No findings yet" body="Run the AI review to check the set." />
      ) : (
        <>
          <Stats items={[
            { label: "Open", value: count((f) => f.state === "open") },
            { label: "Confirmed", value: count((f) => f.state === "confirmed") },
            { label: "Dismissed", value: count((f) => f.state === "dismissed") },
            { label: d.meta.kind === "tests" ? "Tests with findings" : "Requirements with findings", value: new Set(findings.map((f) => f.payload.req_id)).size, aside: true },
          ]} />
          <div className="filters" style={{ marginBottom: "var(--zyn-s5)" }}>
            <FilterGroup label="Finding" selected={pickCat.selected} onChange={pickCat.onChange}
              options={cats.map((c) => ({ value: c, label: c, count: count((f) => f.payload.category === c) }))} />
            {d.ai_available !== false && <FilterGroup label="Found by" selected={pickSrc.selected} onChange={pickSrc.onChange}
              options={SOURCES.map((s) => ({ ...s, count: count((f) => f.payload.source === s.value) }))} />}
            <FilterGroup label="Status" selected={pickState.selected} onChange={pickState.onChange}
              options={STATES.map((s) => ({ value: s, label: cap(s), count: count((f) => f.state === s) }))} />
          </div>
          {multi && (
            <div className="toolbar">
              <Switch checked={onlyStable} onChange={setOnlyStable}
                label="Only AI findings seen in every pass (code findings always shown)" />
            </div>
          )}
          <Cards count={shown.length} style={{ marginTop: "var(--zyn-s5)" }}>
            <AnimatePresence mode="popLayout" initial={false}>
              {shown.map((f, i) => <FindingCard key={f.item_id} f={f} index={i} reasons={d.dismiss_reasons} tests={d.ai_available === false} />)}
            </AnimatePresence>
          </Cards>
          {!shown.length && <Empty title="Nothing matches these filters" body="Turn a filter back on to see more."
            action={<Button onClick={() => { pickCat.onChange(new Set(cats)); pickSrc.onChange(new Set(SOURCES.map((s) => s.value))); pickState.onChange(new Set(STATES)); setOnlyStable(false); }}>Show everything</Button>} />}
          <div className="row" style={{ marginTop: "var(--zyn-s5)" }}>{moreBtn}</div>
        </>
      )}
    </>
  );
}

/** The test's code: the first lines with the evidence marked, the whole test on request. */
function TestCode({ text, evidence }: { text: string; evidence: string }) {
  const lines = text.split(/\r?\n/);
  const at = Math.max(0, lines.findIndex((l) => evidence && l.includes(evidence)));
  const start = Math.max(0, Math.min(at - 3, lines.length - 12));
  const short = lines.slice(start, start + 12).join(String.fromCharCode(10));
  return (
    <>
      <div className="pre"><Highlight text={short} evidence={evidence} /></div>
      {lines.length > 12 && <Disclosure label={`Whole test (${lines.length} lines)`}><div className="pre">{text}</div></Disclosure>}
    </>
  );
}

function FindingCardInner({ f, index, reasons, tests }: { f: any; index: number; reasons: string[]; tests?: boolean }) {
  const p = f.payload;
  const [reason, setReason] = useState<string>();
  const who = p.source === "code" ? "code check" : `AI reviewer (${f.created_by})`;
  const st = f.stability;
  const prior = p.prior;
  const decision: Decision = { status: f.status, block_approve: null, needs_reason: false, reasons: [], earlier: null };
  const verb = (x: string) => x === "approved" ? "confirmed" : x === "rejected" ? "dismissed" : x;

  return (
    <Card index={index}>
      <CardHead id={p.req_id} meta={[p.category, `found by ${who}`]}
        badge={<Badge text={f.state} tone={STATE_TONE[f.state as State] ?? "muted"} />} />
      {tests ? <TestCode text={p.requirement_text} evidence={p.evidence} />
        : <ItemText><Highlight text={p.requirement_text} evidence={p.evidence} /></ItemText>}
      {st && <div className="chips"><Chip tone={st.seen === st.passes ? "ok" : "warn"}>Seen in {st.seen} of {st.passes} AI passes</Chip></div>}
      {p.evidence_found
        ? <p className="small quiet">Quoted words located in the {tests ? "test" : "requirement"}: “{p.evidence}”</p>
        : <Msg tone="bad">The quoted words “{p.evidence}” are not in the {tests ? "test" : "requirement"} text (code check). Treat this finding with caution.</Msg>}
      <p className="small">{p.explanation}</p>
      {f.also.length > 0 && <p className="small quiet">Also reported by: {f.also.join(", ")}</p>}
      {f.record && <p className="small quiet">{f.record.label}</p>}
      <p className="small quiet">Question for the author: {p.question_for_author}
        {p.related_ids?.length > 0 && <> · Related: {p.related_ids.join(", ")}</>}</p>
      {prior && <Msg tone="info">Same finding on the same text was {verb(prior.decision)} by {prior.by} in
        run {prior.run_id}{prior.comment ? `: ${prior.comment}` : "."}</Msg>}
      <DecisionBar itemId={f.item_id} decision={decision} labels={["Confirm", "Dismiss"]}
        comment={reason && reason !== NO_REASON ? reason : undefined}
        extra={<Select value={reason} onChange={setReason} placeholder="Reason, if dismissing"
          label="Dismissal reason (optional)"
          options={[{ value: NO_REASON, label: "No reason" }, ...reasons.map((r) => ({ value: r, label: r }))]} />} />
    </Card>
  );
}

function Requirements({ d }: { d: any }) {
  const rows = (d.requirements as any[]).map((r) => ({ ...r, cats: r.findings.join(", ") }));
  return (
    <Table rows={rows} cols={[
      { key: "id", label: "ID", mono: true }, { key: "heading", label: "Heading" },
      { key: "text", label: "Requirement" }, { key: "cats", label: "Findings" },
      { key: "open", label: "Open", mono: true },
    ]} />
  );
}

/** Memoised: a decision on one card does not re-render the others. */
const FindingCard = memo(FindingCardInner);
