// Sift run: 1. section mapping, 2. requirements, 3. export, audit log.

import { ArrowRight, CheckCheck, ListChecks, Pencil, Sparkles, Wand2 } from "../components/icons";
import { AnimatePresence } from "motion/react";
import { useMemo, useState, memo } from "react";
import { useEdit, type Status } from "../lib/api";
import { useStartStage } from "../lib/jobs";
import { useReviewer } from "../lib/reviewer";
import { DecisionBar } from "../components/Decision";
import { Drawer } from "../components/Drawer";
import { Button, Card, CardHead, Checkbox, Disclosure, Empty, FilterGroup, Field, Msg, PageHeader,
  Select, Stats, StatusBadge, Switch, Tabs, useHidden, useProgressive, Cards } from "../components/ui";
import { useWrite, post } from "../lib/api";
import { AuditTab, ExportTab, JobsStrip } from "./common";
import { RequirementCard } from "./RequirementCard";

const STATUSES: Status[] = ["proposed", "edited", "approved", "rejected"];
const cap = (s: string) => s[0].toUpperCase() + s.slice(1);

export function countStats(c: Record<Status, number>) {
  return STATUSES.map((s) => ({ label: cap(s), value: c[s] ?? 0 }));
}

export function SiftView({ data }: { data: any }) {
  const [tab, setTab] = useState("map");
  const d = data;
  return (
    <>
      <PageHeader kicker="Sift" title={d.doc.title}
        sub={`Source: ${d.doc.filename} · Converter: ${d.doc.converter} · sha256 ${d.doc.sha256.slice(0, 16)}… · Taxonomy: ${d.taxonomy.label}`} />
      <JobsStrip jobKey={d.run_id} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "map", label: "1. Section mapping", count: d.mappings.length },
        { value: "req", label: "2. Requirements", count: d.requirements.length },
        { value: "export", label: "3. Export" }, { value: "audit", label: "Audit log" },
      ]}>
        {tab === "map" && <Mappings d={d} />}
        {tab === "req" && <Requirements d={d} />}
        {tab === "export" && <ExportTab runId={d.run_id} label="Export JSON, Excel and ReqIF"
          disabled={!d.approved_count}
          intro={`${d.approved_count} approved of ${d.requirements.length} requirements. Only approved requirements are exported.`}
          after={() => "requirements."} />}
        {tab === "audit" && <AuditTab runId={d.run_id} />}
      </Tabs>
    </>
  );
}

function useBulk(runId: string) {
  return useWrite((kind: string, reviewer) => post("/api/bulk", { kind, run_id: runId, reviewer }),
    { success: (r) => `Approved ${r.count}` });
}

function Mappings({ d }: { d: any }) {
  const { canAct, noActReason } = useReviewer();
  const bulk = useBulk(d.run_id);
  const [read, setRead] = useState(false);
  const rated = (d.mappings as any[]).filter((m) => d.bulk_mappings.includes(m.item_id));
  const rating = Number(d.bulk_mapping_rating ?? 0.9).toFixed(2);
  return (
    <>
      <Stats items={countStats(d.mapping_counts)} />
      {rated.length > 0 && (
        <div className="card">
          <Disclosure label={`Approve ${rated.length} pending mappings the model rated ${rating} or above`}>
            <p className="small quiet">The rating is the model's own estimate. It has not been shown to predict correctness, so read each section and its subsystem before ticking the box.</p>
            <ul className="small">{rated.map((m) => <li key={m.item_id}><code>§{m.payload.number || "-"}</code> {m.payload.heading} → {m.payload.subsystem_id}</li>)}</ul>
            <Checkbox checked={read} onChange={setRead} label={`I have read these ${rated.length} mappings`} />
            <div><Button variant="primary" icon={CheckCheck} disabled={!canAct || !read}
              tip={!canAct ? noActReason : !read ? "Tick the box first" : undefined} busy={bulk.isPending}
              onClick={() => bulk.mutate("mappings")}>Approve them</Button></div>
          </Disclosure>
        </div>
      )}
      <Cards count={d.mappings.length}>
        {d.mappings.map((m: any, i: number) => <MappingCard key={m.item_id} m={m} index={i} subsystems={d.taxonomy.subsystems} />)}
      </Cards>
    </>
  );
}

function MappingCardInner({ m, index, subsystems }: { m: any; index: number; subsystems: { id: string; name: string }[] }) {
  const p = m.payload;
  const { canAct, noActReason } = useReviewer();
  const edit = useEdit();
  const [open, setOpen] = useState(false);
  const [sub, setSub] = useState(p.subsystem_id);
  return (
    <Card index={index}>
      <CardHead id={`§${p.number || "-"}`} title={p.heading}
        meta={[`→ ${p.subsystem_id}`, `model self-rating ${p.confidence.toFixed(2)}`]}
        badge={<StatusBadge status={m.status} />} />
      <p className="small quiet">{p.rationale}</p>
      {p.text_preview && <Disclosure label="Section text (preview)"><div className="pre">{p.text_preview}</div></Disclosure>}
      <DecisionBar itemId={m.item_id} decision={m.decision}
        extra={<Button variant="ghost" icon={Pencil} className="push" data-key="e" onClick={() => setOpen(true)}>Change subsystem</Button>} />
      <Drawer open={open} onOpenChange={setOpen} title={`§${p.number || "-"} ${p.heading}`}
        description="Saved as a new version of this mapping."
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="primary" disabled={!canAct || sub === p.subsystem_id} tip={!canAct ? noActReason : sub === p.subsystem_id ? "Choose a different subsystem first" : undefined} busy={edit.isPending}
            onClick={() => edit.mutate({ item_id: m.item_id, kind: "subsystem", subsystem_id: sub }, { onSuccess: () => setOpen(false) })}>Save</Button>
        </>}>
        <Field label="Subsystem">
          <Select value={sub} onChange={setSub} options={subsystems.map((s) => ({ value: s.id, label: `${s.id}: ${s.name}` }))} />
        </Field>
        <p className="small quiet">{p.rationale}</p>
      </Drawer>
    </Card>
  );
}

function Requirements({ d }: { d: any }) {
  const { canAct, noActReason } = useReviewer();
  const start = useStartStage(d.run_id);
  const bulk = useBulk(d.run_id);
  const reqs: any[] = d.requirements;
  const subs = useMemo(() => [...new Set(reqs.map((r) => r.payload.subsystem_id as string))].sort(), [reqs]);
  const subF = useHidden(subs);
  const statusF = useHidden(STATUSES as Status[]);
  const [attention, setAttention] = useState(false);
  const [read, setRead] = useState(false);
  const shownAll = reqs.filter((r) => subF.selected.has(r.payload.subsystem_id)
    && statusF.selected.has(r.status) && (!attention || r.needs_attention));
  const { shown, more } = useProgressive(shownAll);
  const clean = reqs.filter((r) => d.bulk_requirements.includes(r.item_id));

  return (
    <>
      <p className="small quiet">
        {d.approved_sections} approved sections with requirements · {d.waiting_sections} waiting for extraction. Only approved mappings are extracted.</p>
      <div className="toolbar">
        <Button variant={reqs.length ? "plain" : "primary"} icon={ArrowRight} disabled={!canAct || !d.waiting_sections}
          tip={!canAct ? noActReason : !d.waiting_sections ? "No approved section is waiting. Approve mappings in tab 1 first." : undefined}
          onClick={() => start("extract")}>Extract requirements from {d.waiting_sections} approved sections</Button>
        {reqs.length > 0 && <Button icon={Sparkles} disabled={!canAct || !d.clarify_candidates}
          tip={!canAct ? noActReason : !d.clarify_candidates ? "No requirement has flagged source wording" : "Asks the generator model how vague source wording could be made testable. Missing values come back as <TBD: ...> placeholders, never invented. Advice only."}
          onClick={() => start("clarify")}>Propose clarifications for {d.clarify_candidates} flagged requirements</Button>}
      </div>
      {!reqs.length ? (
        <Empty icon={ListChecks} title="No requirements yet" body="Approve section mappings in tab 1, then extract." />
      ) : (
        <>
          <Stats items={countStats(d.requirement_counts)} />
          <div className="filters">
            <FilterGroup label="Subsystem" selected={subF.selected} onChange={subF.onChange}
              options={subs.map((s) => ({ value: s, label: s, count: reqs.filter((r) => r.payload.subsystem_id === s).length }))} />
            <FilterGroup label="Status" selected={statusF.selected} onChange={statusF.onChange}
              options={STATUSES.map((s) => ({ value: s, label: cap(s), count: d.requirement_counts[s] ?? 0 }))} />
          </div>
          <div className="toolbar">
            <Switch checked={attention} onChange={setAttention} label="Only items needing attention (a check failed or the AI objected)" />
          </div>
          {clean.length > 0 && (
            <div className="card">
              <Disclosure label={`Approve ${clean.length} requirements where every check passed and the AI reviewer accepted`}>
                <p className="small quiet">Concrete checks only: quote located, modal verb kept, values from the source, vague words flagged, no open placeholders, AI accepted. Read them before ticking the box.</p>
                <ul className="small">{clean.map((r) => <li key={r.item_id}><code>{r.display_id}</code> {r.payload.text}</li>)}</ul>
                <Checkbox checked={read} onChange={setRead} label={`I have read these ${clean.length} requirements`} />
                <div><Button variant="primary" icon={Wand2} disabled={!canAct || !read} tip={!canAct ? noActReason : !read ? "Tick the box first" : undefined} busy={bulk.isPending}
                  onClick={() => bulk.mutate("requirements")}>Approve them</Button></div>
              </Disclosure>
            </div>
          )}
          {d.missed.length > 0 && (
            <Msg tone="warn"><Disclosure label={`AI reviewer: possible missed requirements (${d.missed.length})`}>
              <ul>{d.missed.map((m: any, i: number) => <li key={i}>§{m.section}: {m.text}</li>)}</ul>
            </Disclosure></Msg>
          )}
          <Cards count={shown.length}>
            <AnimatePresence mode="popLayout" initial={false}>
              {shown.map((r, i) => <RequirementCard key={r.item_id} c={r} index={i} />)}
            </AnimatePresence>
          </Cards>
          {!shown.length && <Empty title="Nothing matches these filters" body="Turn a filter back on to see more."
            action={<Button onClick={() => { subF.reset(); statusF.reset(); setAttention(false); }}>Show everything</Button>} />}
          <div className="row">{more}</div>
        </>
      )}
    </>
  );
}

/** Memoised: a decision on one card does not re-render the others. */
const MappingCard = memo(MappingCardInner);
