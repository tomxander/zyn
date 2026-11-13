// The decision row on every card: one primary (the decision that moves the item forward),
// the opposite as a plain button, and a reason picker when the AI reviewer objected.

import { Check, X } from "./icons";
import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { useDecide, type Decision } from "../lib/api";
import { useReviewer } from "../lib/reviewer";
import { Button, Field, Select } from "./ui";
import { T_BASE } from "./motion";

const OTHER = "Other (type a reason)";

export function DecisionBar({ itemId, decision, labels = ["Approve", "Reject"], extra, comment }: {
  itemId: string; decision: Decision; labels?: [string, string]; extra?: ReactNode;
  /** A comment sent with the opposite decision (e.g. a dismissal reason). */
  comment?: string;
}) {
  const { reviewer } = useReviewer();
  const decide = useDecide();
  const [pick, setPick] = useState<string>();
  const [other, setOther] = useState("");
  const reason = pick === OTHER ? other.trim() : pick ?? "";
  const { status, needs_reason, block_approve } = decision;
  const noName = !reviewer ? "Enter your name as reviewer first" : undefined;

  return (
    <div className="stack">
      <AnimatePresence initial={false}>
        {needs_reason && status !== "approved" && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} transition={T_BASE}>
            <div className="stack">
              {decision.earlier && (
                <p className="small quiet">{decision.earlier.by} approved the same wording over an AI
                  objection in run {decision.earlier.run_id}. That reason is offered first.</p>
              )}
              <Field label="The AI reviewer objected. Reason for approving anyway">
                <Select value={pick} onChange={setPick} placeholder="Choose a reason"
                  options={[...decision.reasons, OTHER].map((r) => ({ value: r, label: r }))} />
              </Field>
              {pick === OTHER && <input className="input" placeholder="Reason" value={other}
                onChange={(e) => setOther(e.target.value)} />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <div className="card-actions">
        <Button variant="primary" wide icon={Check} data-key="a"
          disabled={!!noName || !!block_approve || status === "approved" || (needs_reason && !reason)}
          tip={noName ?? block_approve ?? (needs_reason && !reason ? "Choose a reason first" : undefined)}
          onClick={() => decide.mutate({ item_id: itemId, decision: "approved", comment: reason || undefined })}>
          {labels[0]}
        </Button>
        <Button wide icon={X} data-key="r"
          disabled={!!noName || status === "rejected"} tip={noName}
          onClick={() => decide.mutate({ item_id: itemId, decision: "rejected", comment })}>
          {labels[1]}
        </Button>
        {extra}
      </div>
    </div>
  );
}
