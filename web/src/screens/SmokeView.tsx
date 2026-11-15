// Smoke test and Assay (benchmark) runs: the run's items if it has any, and its audit log.
// A benchmark run has no items to review, so it opens on the audit log.

import { ListChecks } from "../components/icons";
import { useState } from "react";
import { Empty, PageHeader, Stats, Tabs } from "../components/ui";
import { AuditTab } from "./common";
import { RequirementCard } from "./RequirementCard";
import { countStats } from "./SiftView";

export function SmokeView({ data: d }: { data: any }) {
  const hasItems = d.requirements.length > 0;
  const [tab, setTab] = useState(hasItems ? "req" : "audit");
  const assay = d.tool === "Assay";
  // A smoke run's note is its model settings ("generator=… reviewer=…"), not a title.
  const title = assay ? d.note || `Run ${d.run_id}` : "Smoke test: synthetic fuel-gauge spec";
  const sub = assay ? "Source: benchmark data, scored against its answer key · Run: " + d.run_id
    : `Source: synthetic fuel-gauge specification${d.note ? ` · Models: ${d.note}` : ""} · Run: ${d.run_id}`;
  return (
    <>
      <PageHeader kicker={d.tool} title={title} sub={sub} />
      <Tabs value={tab} onChange={setTab} tabs={[
        ...(hasItems ? [{ value: "req", label: "Requirements", count: d.requirements.length }] : []),
        { value: "audit", label: assay ? "Model calls and audit log" : "Audit log" },
      ]}>
        {tab === "req" && (d.requirements.length ? (
          <>
            <Stats items={countStats(d.requirement_counts)} />
            <div className="cards">{d.requirements.map((r: any, i: number) => <RequirementCard key={r.item_id} c={r} index={i} />)}</div>
          </>
        ) : <Empty icon={ListChecks} title="No items in this run" body="This run recorded model calls only. See the audit log." />)}
        {tab === "audit" && <AuditTab runId={d.run_id} />}
      </Tabs>
    </>
  );
}
