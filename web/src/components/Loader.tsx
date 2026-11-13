// Thinking and loading: a pixel grid that moves in one of four calm patterns, a label with
// a slow shimmer, the elapsed time, and a live trace of what the stage has done so far.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState, type CSSProperties } from "react";
import { toast } from "sonner";
import { api, type Job } from "../lib/api";
import { X } from "./icons";
import { Button, Msg } from "./ui";
import { enter, T_BASE } from "./motion";

export type Pattern = "orbit" | "wave" | "churn" | "pulse";
// Order in which the 9 cells light up, per pattern (index = cell, value = step).
const STEPS: Record<Pattern, number[]> = {
  orbit: [0, 1, 2, 7, 8, 3, 6, 5, 4],     // around the edge, centre last
  wave: [0, 1, 2, 0, 1, 2, 0, 1, 2],      // left to right
  churn: [3, 7, 1, 5, 0, 6, 2, 8, 4],     // scattered
  pulse: [2, 1, 2, 1, 0, 1, 2, 1, 2],     // centre out
};

export function Pixels({ pattern = "orbit" }: { pattern?: Pattern }) {
  const steps = STEPS[pattern];
  const max = Math.max(...steps) + 1;
  return (
    <span className="pixels" aria-hidden>
      {steps.map((s, i) => <i key={i} style={{ animationDelay: `calc(var(--zyn-loop) * ${s / max})` } as CSSProperties} />)}
    </span>
  );
}

export const Shimmer = ({ children }: { children: string }) => <span className="shimmer">{children}</span>;

/** Ticks locally between polls so the seconds move smoothly. */
function Elapsed({ base, running }: { base: number; running: boolean }) {
  const [t, setT] = useState(base);
  useEffect(() => { setT(base); }, [base]);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setT((v) => v + 0.1), 100);
    return () => clearInterval(id);
  }, [running]);
  return <span className="elapsed">{t.toFixed(1)}s</span>;
}

export function Loading({ label, pattern = "orbit" }: { label: string; pattern?: Pattern }) {
  const [t0] = useState(() => Date.now());
  const [t, setT] = useState(0);
  useEffect(() => { const id = setInterval(() => setT((Date.now() - t0) / 1000), 100); return () => clearInterval(id); }, [t0]);
  return (
    <motion.div className="loader" variants={enter} initial="hidden" animate="show" role="status">
      <Pixels pattern={pattern} /><Shimmer>{label}</Shimmer>
      {t > 0.6 && <span className="elapsed">{t.toFixed(1)}s</span>}
    </motion.div>
  );
}

/** Failures grouped by reason, so eleven identical errors read as one line. */
function FailedList({ failed }: { failed: Record<string, string> }) {
  const groups = new Map<string, string[]>();
  for (const [k, v] of Object.entries(failed)) {
    const reason = String(v).replace(/^[a-z_]+:\s*/, "");
    groups.set(reason, [...(groups.get(reason) ?? []), k]);
  }
  return (
    <div className="stack">
      {[...groups].map(([reason, keys]) => (
        <Msg key={reason} tone="bad"><b>{keys.length} failed</b> ({keys.join(", ")}): {reason}</Msg>
      ))}
    </div>
  );
}

/** A background stage: polls the job, shows the trace, refreshes the run when done. */
export function JobPanel({ job: start, onDone, onClose, pattern = "orbit" }:
  { job: Job; onDone?: (j: Job) => void; onClose?: () => void; pattern?: Pattern }) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["job", start.id], queryFn: () => api<Job>(`/api/jobs/${start.id}`),
    initialData: start, refetchInterval: (q) => (q.state.data?.state === "running" ? 700 : false),
  });
  const job = data ?? start;
  useEffect(() => {
    if (job.state === "running") return;
    qc.invalidateQueries({ queryKey: ["run"] });
    qc.invalidateQueries({ queryKey: ["runs"] });
    const failed = job.result?.failed && Object.keys(job.result.failed).length;
    if (job.state === "done" && !failed) toast.success(`${job.label.split(",")[0]}: done in ${job.elapsed}s`);
    else if (job.state === "done") toast.warning(`Finished with ${failed} failed. See the list on the page.`);
    else toast.error(job.error || "The stage failed");
    onDone?.(job);
  }, [job.state]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <motion.div className="job" layout variants={enter} initial="hidden" animate="show" exit="exit">
      <div className="loader" role="status" aria-live="polite">
        {job.state === "running" ? <Pixels pattern={pattern} /> : null}
        {job.state === "running" ? <Shimmer>{job.label}</Shimmer>
          : <span className="small">{job.label}</span>}
        <Elapsed base={job.elapsed} running={job.state === "running"} />
        {job.state !== "running" && onClose &&
          <Button variant="ghost" size="sm" icon={X} aria-label="Close" onClick={onClose} />}
      </div>
      {job.trace.length > 0 && (
        <ul className="trace">
          <AnimatePresence initial={false}>
            {job.trace.map((s) => (
              <motion.li key={s.ts + s.action + s.object} layout initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }} transition={T_BASE}>
                {s.text}{s.object && <code>{s.object.split("@")[0]}</code>}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
      {job.state === "failed" && <Msg tone="bad">{job.error}</Msg>}
      {job.state === "done" && job.result?.failed && Object.keys(job.result.failed).length > 0 && (
        <FailedList failed={job.result.failed} />
      )}
    </motion.div>
  );
}
