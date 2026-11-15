// Anvil run: 1. test specs, 2. generated cases, 3. export, audit log.

import { Cog, FlaskConical, Pencil, RefreshCw, RotateCcw } from "../components/icons";
import { AnimatePresence } from "motion/react";
import { useState, memo } from "react";
import { useAction, useEdit } from "../lib/api";
import { useStartStage } from "../lib/jobs";
import { useReviewer } from "../lib/reviewer";
import { DecisionBar } from "../components/Decision";
import { Drawer } from "../components/Drawer";
import { Button, Card, CardHead, Empty, Field, FilterGroup, ItemText, Msg, PageHeader, Select,
  Stats, StatusBadge, Switch, Table, Tabs, useHidden, useProgressive, Cards } from "../components/ui";
import { AuditTab, ExportTab, JobsStrip } from "./common";
import { countStats } from "./SiftView";

const NONE = "__none";
const fmt = (v: unknown) => typeof v === "number" ? String(Number(v.toPrecision(6))) : String(v);
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

export function AnvilView({ data }: { data: any }) {
  const [tab, setTab] = useState("specs");
  const d = data;
  const m = d.meta;
  return (
    <>
      <PageHeader kicker="Anvil" title={`Test cases from Sift run ${m.sift_run}`}
        sub={`Input: ${m.requirements} approved requirements · CAN database: ${m.dbc_file} (sha256 ${m.dbc_sha256.slice(0, 16)}…) · Method: the model proposes a template per requirement; code checks it, generates the cases and tests them against injected faults`} />
      <JobsStrip jobKey={d.run_id} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "specs", label: "1. Test specs", count: d.specs.length },
        { value: "cases", label: "2. Cases", count: d.case_count },
        { value: "export", label: "3. Export" }, { value: "audit", label: "Audit log" },
      ]}>
        {tab === "specs" && <Specs d={d} />}
        {tab === "cases" && <Cases d={d} />}
        {tab === "export" && <ExportTab runId={d.run_id} label="Export test cases"
          disabled={!d.case_count}
          intro="Exports every generated case as JSON, Excel and a pytest module. The pytest module is linted here and has not been run against any hardware."
          after={(res) => {
            const out = res.left_out?.length ?? 0;
            const lint: string[] = res.lint ?? [];
            return <>current cases{out ? ` (${out} stale or superseded left out)` : ""}. Lint: {lint.length ? lint.slice(0, 3).join("; ") : "clean"}.</>;
          }} />}
        {tab === "audit" && <AuditTab runId={d.run_id} />}
      </Tabs>
    </>
  );
}

// ---- 1. test specs -----------------------------------------------------------------------

function Specs({ d }: { d: any }) {
  const { canAct, noActReason } = useReviewer();
  const start = useStartStage(d.run_id);
  const gen = useAction(d.run_id);
  const specs: any[] = d.specs;
  const templates: string[] = d.templates;
  const tplF = useHidden(templates);
  const [onlyBad, setOnlyBad] = useState(false);
  const shownAll = specs.filter((s) => tplF.selected.has(s.payload.template)
    && (!onlyBad || s.payload.problems.length));
  const { shown, more } = useProgressive(shownAll);
  const noName = !canAct ? noActReason : undefined;
  const missing: string[] = d.missing_specs;
  const res = gen.data;

  return (
    <>
      <Stats items={countStats(d.spec_counts)} />
      {d.formal?.issues.length > 0 && (
        <Msg tone="warn">
          {plural(d.formal.issues.length, "contradiction")} between approved specs (formal set check, code check):
          <ul>{d.formal.issues.map((i: any) => <li key={i.requirements.join("+") + i.kind}><b>{i.requirements.join(" and ")}</b>: {i.explanation}</li>)}</ul>
        </Msg>
      )}
      {d.formal?.uncovered_outputs.length > 0 && (
        <Msg tone="info">No approved spec checks these cluster outputs (code check): {d.formal.uncovered_outputs.join(", ")}</Msg>
      )}
      {missing.length > 0 && (
        <Msg tone="warn">
          {missing.length} approved requirements have no spec (a model call failed): {missing.join(", ")}
          <div className="row">
            <Button icon={RotateCcw} disabled={!!noName} tip={noName}
              onClick={() => start("forge_resume")}>Retry those requirements</Button>
          </div>
        </Msg>
      )}
      <div className="toolbar">
        <Button variant={d.ready ? "primary" : "plain"} icon={Cog} disabled={!canAct || !d.ready}
          busy={gen.isPending}
          tip={noName ?? (!d.ready ? "No approved spec is waiting for cases. Approve specs in tab 1 first." : "Code only, no model calls. Each spec's cases are also run against simulated faults.")}
          onClick={() => gen.mutate({ name: "forge_generate" })}>
          Generate cases for {plural(d.ready, "approved spec")}</Button>
        {d.repropose > 0 && <Button icon={RefreshCw} disabled={!!noName}
          tip={noName ?? "Asks the model again with the current prompt, for these specs only. Each answer becomes a new version for you to decide; approved specs are untouched."}
          onClick={() => start("forge_repropose")}>
          Propose again for {plural(d.repropose, "spec")} (rejected, failing checks, or requirement changed)</Button>}
      </div>
      {res && (
        res.skipped?.length
          ? <Msg tone="warn">Generated {plural(res.cases, "case")}. {plural(res.skipped.length, "spec")} skipped:
              <ul>{res.skipped.map((s: any) => <li key={s.spec}><code>{s.spec.split("@")[0]}</code> {s.problems.join("; ")}</li>)}</ul></Msg>
          : <Msg tone="ok">Generated {plural(res.cases, "case")}.</Msg>
      )}
      {!specs.length ? (
        <Empty icon={FlaskConical} title="No test specs yet" body="The model proposes one spec per approved requirement. Check the running stage above." />
      ) : (
        <>
          <div className="filters">
            <FilterGroup label="Template" selected={tplF.selected} onChange={tplF.onChange}
              options={templates.map((t) => ({ value: t, label: t, count: specs.filter((s) => s.payload.template === t).length }))} />
          </div>
          <div className="toolbar">
            <Switch checked={onlyBad} onChange={setOnlyBad}
              label={`Only specs failing code checks (${specs.filter((s) => s.payload.problems.length).length})`} />
          </div>
          <Cards count={shown.length}>
            <AnimatePresence mode="popLayout" initial={false}>
              {shown.map((s, i) => <SpecCard key={s.item_id} s={s} index={i} options={d.edit_options} />)}
            </AnimatePresence>
          </Cards>
          {!shown.length && <Empty title="Nothing matches these filters" body="Turn a filter back on to see more."
            action={<Button onClick={() => { tplF.reset(); setOnlyBad(false); }}>Show everything</Button>} />}
          <div className="row">{more}</div>
        </>
      )}
    </>
  );
}

const REQ_STATE: Record<string, (now: string) => string> = {
  changed: (now) => `The requirement has a newer approved version: “${now}”. Propose this spec again.`,
  pending: (now) => `The requirement has an update awaiting approval: “${now}”.`,
  dropped: () => "The requirement is no longer approved (rejected). Reject this spec; its cases are stale.",
};

function SpecCardInner({ s, index, options }: { s: any; index: number; options: any }) {
  const p = s.payload;
  const [open, setOpen] = useState(false);
  const params = Object.entries(s.params as Record<string, unknown>);
  return (
    <Card index={index}>
      <CardHead id={p.req_id} meta={[`template ${p.template}`, `v${s.version}`]}
        badge={<StatusBadge status={s.status} />} />
      <ItemText>{p.requirement_text}</ItemText>
      {s.statement && <p className="small"><span className="quiet">Formal statement: </span>{s.statement}</p>}
      {params.length > 0 && (
        <p className="small">{params.map(([k, v], i) => (
          <span key={k}>{i > 0 && " · "}<code>{k}</code> = <b>{fmt(v)}</b></span>
        ))}</p>
      )}
      {(p.value_sources ?? []).map((src: any, i: number) => (
        <p key={i} className="small quiet">{src.param} from: “{src.quote}”</p>
      ))}
      {p.problems.length > 0 && (
        <Msg tone="bad">Code checks failed: {p.problems.join("; ")}. Edit the spec or reject it; cases are only generated from specs that pass.</Msg>
      )}
      {s.requirement_state !== "current" && REQ_STATE[s.requirement_state] && (
        <Msg tone="warn">{REQ_STATE[s.requirement_state](s.requirement_now ?? "")}</Msg>
      )}
      {(s.formal_issues ?? []).map((x: string) => <Msg key={x} tone="warn">{x} (formal set check, code check)</Msg>)}
      {p.missing?.length > 0 && <Msg tone="warn">Not given by the requirement: {p.missing.join("; ")}</Msg>}
      {p.manual_test_idea && <Msg tone="info">Manual test idea: {p.manual_test_idea}</Msg>}
      {(p.assumptions ?? []).map((a: string) => <p key={a} className="small quiet">Assumption: {a}</p>)}
      {!p.problems.length && (
        <p className="small quiet">Code checks passed: template complete, signals in the DBC, values in range and traced to the requirement text.</p>
      )}
      <DecisionBar itemId={s.item_id} decision={s.decision}
        extra={<Button variant="ghost" icon={Pencil} className="push" data-key="e" onClick={() => setOpen(true)}>Edit spec</Button>} />
      <EditSpec key={s.version} s={s} options={options} open={open} onOpenChange={setOpen} />
    </Card>
  );
}

function EditSpec({ s, options, open, onOpenChange }: {
  s: any; options: any; open: boolean; onOpenChange: (v: boolean) => void;
}) {
  const p = s.payload;
  const { canAct, noActReason } = useReviewer();
  const edit = useEdit();
  const nums: string[] = options.numbers;
  const [f, setF] = useState(() => ({
    template: p.template as string,
    input_signal: p.input_signal ?? NONE, output_signal: p.output_signal ?? NONE,
    message: p.message ?? NONE, direction: p.direction ?? NONE,
    manual_test_idea: p.manual_test_idea ?? "",
    nums: Object.fromEntries(nums.map((k) => [k, p[k] == null ? "" : fmt(p[k])])) as Record<string, string>,
  }));
  const [note, setNote] = useState("");
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  const bad = nums.filter((k) => f.nums[k].trim() && !Number.isFinite(Number(f.nums[k])));
  const opts = (list: string[]) => [{ value: NONE, label: "None" }, ...list.map((v) => ({ value: v, label: v }))];
  const orNull = (v: string) => (v === NONE ? null : v);

  const save = () => {
    const fields: Record<string, unknown> = {
      template: f.template, input_signal: orNull(f.input_signal), output_signal: orNull(f.output_signal),
      message: orNull(f.message), direction: orNull(f.direction),
      manual_test_idea: f.manual_test_idea.trim() || null,
    };
    for (const k of nums) fields[k] = f.nums[k].trim() ? Number(f.nums[k]) : null;
    edit.mutate({ item_id: s.item_id, kind: "spec", fields, comment: note },
      { onSuccess: () => { onOpenChange(false); setNote(""); } });
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange} title={`Edit spec ${p.req_id}`}
      description="Saved as a new version and checked again by code. The proposed version stays in the record."
      footer={<>
        <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant="primary" disabled={!canAct || bad.length > 0} busy={edit.isPending}
          tip={!canAct ? noActReason : bad.length ? "Fix the numbers first" : undefined}
          onClick={save}>Save as new version</Button>
      </>}>
      <ItemText>{p.requirement_text}</ItemText>
      <div className="fields">
        <Field label="Template">
          <Select value={f.template} onChange={(v) => set("template", v)}
            options={(options.templates as string[]).map((t) => ({ value: t, label: t }))} />
        </Field>
        <Field label="Direction">
          <Select value={f.direction} onChange={(v) => set("direction", v)} options={opts(["below", "above"])} />
        </Field>
        <Field label="Input signal">
          <Select value={f.input_signal} onChange={(v) => set("input_signal", v)} options={opts(options.inputs)} />
        </Field>
        <Field label="Output signal">
          <Select value={f.output_signal} onChange={(v) => set("output_signal", v)} options={opts(options.outputs)} />
        </Field>
        <Field label="Message">
          <Select value={f.message} onChange={(v) => set("message", v)} options={opts(options.messages)} />
        </Field>
      </div>
      <div className="fields">
        {nums.map((k) => (
          <Field key={k} label={k}>
            <input className="input" inputMode="decimal" value={f.nums[k]} placeholder="blank"
              onChange={(e) => setF({ ...f, nums: { ...f.nums, [k]: e.target.value } })} />
          </Field>
        ))}
      </div>
      {bad.length > 0 && <Msg tone="bad">Not a number: {bad.join(", ")}.</Msg>}
      <Field label="Manual test idea (when the template is not automatable)">
        <textarea className="textarea" value={f.manual_test_idea} onChange={(e) => set("manual_test_idea", e.target.value)} />
      </Field>
      <Field label="Reason for edit"><input className="input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
    </Drawer>
  );
}

// ---- 2. cases ----------------------------------------------------------------------------

function Cases({ d }: { d: any }) {
  const groups: any[] = d.case_groups;
  if (!d.case_count) return <Empty icon={FlaskConical} title="No cases yet" body="Approve specs in tab 1, then generate." />;
  return (
    <>
      {d.faults_total > 0 && (() => {
        const s = d.fault_score;
        return <>
          <Stats items={[
            { label: "Injected faults detected", value: s.detected, of: s.faults,
              tip: "Each spec's newest cases run against a correct simulation and faulty variants (code check). This tests the tests against a fixed fault list, not the product." },
            { label: "Faults no case detects", value: s.surviving.length },
            { label: "Cases that detect no fault", value: s.cases_detecting_nothing.length,
              tip: "These cases catch none of the injected faults. They may still check something the fault list does not cover." },
            { label: "Specs checked", value: s.specs_checked },
          ]} />
          {s.reference_failed.length > 0 && (
            <Msg tone="bad">Cases fail on the correct simulation for {s.reference_failed.join(", ")} (code check). The spec or the generator is wrong; do not use those cases.</Msg>
          )}
          {s.surviving.length > 0 && (
            <Msg tone="warn">No case detects: {s.surviving.map((f: any) => `${f.requirement_id} (${f.label})`).join("; ")} (code check)</Msg>
          )}
        </>;
      })()}
      {d.stale > 0 && <Msg tone="warn">{d.stale} cases are stale or superseded and are left out of exports.</Msg>}
      <div className="cards">
        {groups.map((g, i) => <CaseGroup key={g.spec_item} g={g} index={i} />)}
      </div>
    </>
  );
}

function CaseGroup({ g, index }: { g: any; index: number }) {
  const fc = g.faults ?? {};
  const faults = Object.values(fc.faults ?? {}) as { fault: string; detected_by: string[] }[];
  return (
    <Card index={index}>
      <CardHead id={g.requirement_id} meta={[g.template, plural(g.cases.length, "case"),
        fc.total ? `detects ${fc.detected} of ${fc.total} injected faults` : null]} />
      {fc.reference_passes === false && (
        <Msg tone="bad">A case fails on the correct simulation: the spec or the generator is wrong. Do not use these cases.</Msg>
      )}
      {faults.filter((f) => !f.detected_by.length).map((f) => (
        <Msg key={f.fault} tone="warn">{f.fault}: no case detects this</Msg>
      ))}
      {faults.filter((f) => f.detected_by.length).map((f) => (
        <p key={f.fault} className="small quiet">Detected: {f.fault}: {f.detected_by.join(", ")}</p>
      ))}
      <Table rows={g.cases} cols={[
        { key: "case_id", label: "Case", mono: true },
        { key: "state", label: "State" },
        { key: "kind", label: "Kind" },
        { key: "title", label: "Title" },
        { key: "expected", label: "Expected" },
        { key: "boundary_rationale", label: "Why" },
        { key: "open_values", label: "Open values", render: (c) => (c.open_values ?? []).join("; ") },
      ]} />
    </Card>
  );
}

/** Memoised: a decision on one card does not re-render the others. */
const SpecCard = memo(SpecCardInner);
