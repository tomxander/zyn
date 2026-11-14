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
  Select, Stats, StatusBadge, Switch, Tabs, useProgressive, Cards } from "../components/ui";
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
        sub={`${d.doc.filename} · converter: ${d.doc.converter} · sha256 ${d.doc.sha256.slice(0, 16)}… · taxonomy: ${d.taxonomy.label}`} />
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
  return (
    <>
      <Stats items={countStats(d.mapping_counts)} />
      {d.bulk_mappings.length > 0 && (
        <div className="stack" style={{ marginBottom: "var(--zyn-s6)" }}>
          <p className="small quiet">The rating is the model's own estimate. It has not been shown to predict correctness, so read the section previews before approving in bulk.</p>
          <div><Button icon={CheckCheck} disabled={!canAct} tip={!canAct ? noActReason : undefined} busy={bulk.isPending}
            onClick={() => bulk.mutate("mappings")}>
            Approve all {d.bulk_mappings.length} pending mappings the model rated 0.90 or above</Button></div>
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
          <Button variant="primary" disabled={!canAct || sub === p.subsystem_id} tip={!canAct ? noActReason : undefined} busy={edit.isPending}
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
  const [pickSub, setPickSub] = useState<Set<string>>(() => new Set(subs));
  const [pickStatus, setPickStatus] = useState<Set<Status>>(() => new Set(STATUSES));
  const [attention, setAttention] = useState(false);
  const [read, setRead] = useState(false);
  const shownAll = reqs.filter((r) => (pickSub.has(r.payload.subsystem_id) || !subs.includes(r.payload.subsystem_id))
    && pickStatus.has(r.status) && (!attention || r.needs_attention));
  const { shown, more } = useProgressive(shownAll);
  const clean = reqs.filter((r) => d.bulk_requirements.includes(r.item_id));

  return (
    <>
      <p className="small quiet" style={{ marginBottom: "var(--zyn-s4)" }}>
        {d.approved_sections} approved sections with requirements · {d.waiting_sections} waiting for extraction. Only approved mappings are extracted.</p>
      <div className="toolbar">
        <Button variant={reqs.length ? "plain" : "primary"} icon={ArrowRight} disabled={!canAct || !d.waiting_sections}
          tip={!canAct ? noActReason : undefined}
          onClick={() => start("extract")}>Extract requirements from {d.waiting_sections} approved sections</Button>
        {reqs.length > 0 && <Button icon={Sparkles} disabled={!canAct || !d.clarify_candidates}
          tip={!canAct ? noActReason : "Asks the generator model how vague source wording could be made testable. Missing values come back as <TBD: ...> placeholders, never invented. Advice only."}
          onClick={() => start("clarify")}>Propose clarifications for {d.clarify_candidates} flagged requirements</Button>}
      </div>
      {!reqs.length ? (
        <Empty icon={ListChecks} title="No requirements yet" body="Approve section mappings in tab 1, then extract." />
      ) : (
        <>
          <Stats items={countStats(d.requirement_counts)} />
          <div className="filters" style={{ marginBottom: "var(--zyn-s5)" }}>
            <FilterGroup label="Subsystem" selected={pickSub} onChange={setPickSub}
              options={subs.map((s) => ({ value: s, label: s, count: reqs.filter((r) => r.payload.subsystem_id === s).length }))} />
            <FilterGroup label="Status" selected={pickStatus} onChange={setPickStatus}
              options={STATUSES.map((s) => ({ value: s, label: cap(s), count: d.requirement_counts[s] ?? 0 }))} />
          </div>
          <div className="toolbar">
            <Switch checked={attention} onChange={setAttention} label="Only items needing attention (a check failed or the AI objected)" />
          </div>
          {clean.length > 0 && (
            <div className="card" style={{ marginBottom: "var(--zyn-s6)" }}>
              <Disclosure label={`Approve ${clean.length} requirements where every check passed and the AI reviewer accepted`}>
                <p className="small quiet">Concrete checks only: quote located, modal verb kept, values from the source, vague words flagged, no open placeholders, AI accepted. Read them before ticking the box.</p>
                <ul className="small">{clean.map((r) => <li key={r.item_id}><code>{r.display_id}</code> {r.payload.text}</li>)}</ul>
                <Checkbox checked={read} onChange={setRead} label={`I have read these ${clean.length} requirements`} />
                <div><Button variant="primary" icon={Wand2} disabled={!canAct || !read} tip={!canAct ? noActReason : undefined} busy={bulk.isPending}
                  onClick={() => bulk.mutate("requirements")}>Approve them</Button></div>
              </Disclosure>
            </div>
          )}
          {d.missed.length > 0 && (
            <Msg tone="warn"><Disclosure label={`AI reviewer: possible missed requirements (${d.missed.length})`}>
              <ul>{d.missed.map((m: any, i: number) => <li key={i}>§{m.section}: {m.text}</li>)}</ul>
            </Disclosure></Msg>
          )}
          <Cards count={shown.length} style={{ marginTop: "var(--zyn-s5)" }}>
            <AnimatePresence mode="popLayout" initial={false}>
              {shown.map((r, i) => <RequirementCard key={r.item_id} c={r} index={i} />)}
            </AnimatePresence>
          </Cards>
          {!shown.length && <Empty title="Nothing matches these filters" body="Turn a filter back on to see more."
            action={<Button onClick={() => { setPickSub(new Set(subs)); setPickStatus(new Set(STATUSES)); setAttention(false); }}>Show everything</Button>} />}
          <div className="row" style={{ marginTop: "var(--zyn-s5)" }}>{more}</div>
        </>
      )}
    </>
  );
}

/** Memoised: a decision on one card does not re-render the others. */
const MappingCard = memo(MappingCardInner);
