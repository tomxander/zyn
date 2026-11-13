import { AnimatePresence } from "motion/react";
import { JobPanel, type Pattern } from "../components/Loader";
import { useJobs } from "../lib/jobs";

/** Stages running (or just finished) for one run. Finished ones fade out after a moment. */
export function JobsStrip({ jobKey, pattern, onDone }: { jobKey: string; pattern?: Pattern; onDone?: (result: any) => void }) {
  const { list, drop } = useJobs(jobKey);
  return (
    <AnimatePresence initial={false}>
      {list.map((j) => (
        <JobPanel key={j.id} job={j} pattern={pattern} onClose={() => drop(j.id)} onDone={(done) => {
          onDone?.(done.result);
          if (done.state === "done" && !Object.keys(done.result?.failed ?? {}).length) setTimeout(() => drop(j.id), 2500);
        }} />
      ))}
    </AnimatePresence>
  );
}
