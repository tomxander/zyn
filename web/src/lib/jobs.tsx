// Running stages, kept per run so they survive tab and run switches.

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { post, type Job } from "./api";
import { useReviewer } from "./reviewer";

interface Ctx { jobs: Record<string, Job[]>; add: (key: string, j: Job) => void; drop: (key: string, id: string) => void }
const C = createContext<Ctx>({ jobs: {}, add: () => {}, drop: () => {} });

export function JobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Record<string, Job[]>>({});
  const add = useCallback((key: string, j: Job) =>
    setJobs((s) => ({ ...s, [key]: [...(s[key] ?? []).filter((x) => x.state === "running"), j] })), []);
  const drop = useCallback((key: string, id: string) =>
    setJobs((s) => ({ ...s, [key]: (s[key] ?? []).filter((x) => x.id !== id) })), []);
  return <C.Provider value={{ jobs, add, drop }}>{children}</C.Provider>;
}

export const useJobs = (key: string) => {
  const { jobs, drop } = useContext(C);
  return { list: jobs[key] ?? [], drop: (id: string) => drop(key, id) };
};

/** Start a stage that runs in the background and show it on the run's page. */
export function useStartStage(runId: string) {
  const { add } = useContext(C);
  const { reviewer } = useReviewer();
  return async (name: string, extra: Record<string, unknown> = {}) => {
    try {
      const res = await post<{ job: Job }>(`/api/runs/${runId}/actions/${name}`, { ...extra, reviewer });
      add(runId, res.job);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };
}

export const useAddJob = () => useContext(C).add;
