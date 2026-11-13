// Smoke and evaluation runs: a single list of requirements, plus the audit log.

import { ListChecks } from "../components/icons";
import { useState } from "react";
import { Empty, PageHeader, Stats, Tabs } from "../components/ui";
import { AuditTab } from "./common";
import { RequirementCard } from "./RequirementCard";
import { countStats } from "./SiftView";

export function SmokeView({ data: d }: { data: any }) {
  const [tab, setTab] = useState("req");
  return (
    <>
      <PageHeader kicker={d.tool} title={`Run ${d.run_id}`} sub={`Workflow ${d.workflow}`} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "req", label: "Requirements", count: d.requirements.length },
        { value: "audit", label: "Audit log" },
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
