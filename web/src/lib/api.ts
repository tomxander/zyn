// Thin client for the Zyn API (harness/api/server.py). Every write sends the reviewer name.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useReviewer } from "./reviewer";

export type Tone = "ok" | "warn" | "info" | "bad" | "muted";
export type Status = "proposed" | "edited" | "approved" | "rejected";

export interface Decision {
  status: Status;
  block_approve: string | null;
  block_decide?: string | null;
  needs_reason: boolean;
  reasons: string[];
  earlier: { by: string; run_id: string } | null;
}

export interface RunSummary { run_id: string; workflow: string; tool: string; note: string; created: string }

export interface Job {
  id: string; run_id: string | null; label: string; state: "running" | "done" | "failed";
  result: any; error: string | null; elapsed: number; steps: number;
  trace: { ts: string; text: string; object: string | null; action: string }[];
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    headers.set("X-Zyn-Request", "1");
  }
  const res = await fetch(path, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || res.statusText, res.status);
  return data as T;
}

export const post = <T = any>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export interface TokenSummary {
  token_id: string;
  label: string;
  created_at: string;
  expires_at: string;
  revoked: boolean;
}

export function useTokens() {
  return useQuery({ queryKey: ["tokens"], queryFn: () => api<TokenSummary[]>("/api/tokens") });
}

export function useCreateToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { label: string; days?: number }) =>
      post<{ token_id: string; secret: string }>("/api/tokens", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useRevokeToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tokenId: string) => post<{ ok: boolean }>(`/api/tokens/${tokenId}/revoke`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens"] }),
    onError: (e: Error) => toast.error(e.message),
  });
}

export function getActiveProject(): string | null {
  if (typeof window === "undefined") return null;
  const p = new URLSearchParams(window.location.search).get("project");
  return p || null;
}

export function useTeamSettings() {
  return useQuery({ queryKey: ["team-settings"], queryFn: () => api("/api/team-settings") });
}

export function useConfig() {
  const p = getActiveProject();
  const url = p ? `/api/config?project=${encodeURIComponent(p)}` : "/api/config";
  return useQuery({
    queryKey: p ? ["config", p] : ["config"],
    queryFn: () => api(url),
    staleTime: 30_000,
  });
}

export function useRuns() {
  const p = getActiveProject();
  const url = p ? `/api/runs?project=${encodeURIComponent(p)}` : "/api/runs";
  return useQuery({
    queryKey: p ? ["runs", p] : ["runs"],
    queryFn: () => api<RunSummary[]>(url),
  });
}

export function useRun(runId: string | null) {
  const p = getActiveProject();
  return useQuery({
    queryKey: ["run", runId, p], enabled: !!runId,
    queryFn: () => api(`/api/runs/${runId}`), placeholderData: (prev) => prev,
  });
}

export function useAudit(runId: string) {
  return useQuery({ queryKey: ["audit", runId], queryFn: () => api(`/api/runs/${runId}/audit`) });
}

/** Any write. Refreshes the run afterwards; errors become a toast. */
export function useWrite<V>(fn: (vars: V, reviewer: string, project?: string | null) => Promise<any>, opts?: {
  success?: (data: any, vars: V) => string | null | void;
}) {
  const qc = useQueryClient();
  const { reviewer } = useReviewer();
  const project = getActiveProject();
  return useMutation({
    mutationFn: (vars: V) => fn(vars, reviewer, project),
    onSuccess: (data, vars) => {
      const msg = opts?.success?.(data, vars);
      if (msg) toast.success(msg);
      qc.invalidateQueries({ queryKey: ["run"] });
      qc.invalidateQueries({ queryKey: ["runs"] });
      qc.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

type DecideVars = { item_id: string; decision: "approved" | "rejected" | "reopened"; comment?: string };

// Labels the screens show for the same status, per workflow (Sift Review, Sift Delta).
const STATES: Record<string, [string, string]> = {
  approved: ["confirmed", "needs action"], rejected: ["dismissed", "no action"],
  proposed: ["open", "open"], edited: ["open", "open"],
};

/** The run view with one item's status changed. Only objects on the path to that item are
 *  copied, so every other card keeps its identity and skips re-rendering. */
function patchStatus(data: any, id: string, status: string): any {
  if (!data || typeof data !== "object") return data;
  if (Array.isArray(data)) {
    let changed = false;
    const out = data.map((x) => { const y = patchStatus(x, id, status); if (y !== x) changed = true; return y; });
    return changed ? out : data;
  }
  if (data.item_id === id && "status" in data) {
    const out: any = { ...data, status };
    if (data.decision) out.decision = { ...data.decision, status };
    if (typeof data.state === "string") {
      const delta = ["needs action", "no action"].includes(data.state) || (data.state === "open" && "label" in data);
      out.state = STATES[status]?.[delta ? 1 : 0] ?? data.state;
    }
    return out;
  }
  let out: any = null;
  for (const [k, v] of Object.entries(data)) {
    const y = patchStatus(v, id, status);
    if (y !== v) { out = out ?? { ...data }; out[k] = y; }
  }
  return out ?? data;
}

function findItem(data: any, id: string): any {
  if (!data || typeof data !== "object") return null;
  if (data.item_id === id) return data;
  for (const v of Object.values(data)) { const f = findItem(v, id); if (f) return f; }
  return null;
}

/** Say it to screen readers: decisions change a badge, which is otherwise silent. */
export function announce(text: string) {
  const el = document.getElementById("zyn-live");
  if (el) { el.textContent = ""; setTimeout(() => { el.textContent = text; }, 30); }
}

const PAST: Record<string, string> = { approved: "approved", rejected: "rejected", reopened: "reopened" };

/** Decide on an item. The badge changes at once; the server confirms or the change rolls
 *  back. A toast offers Undo, which reopens the item (both events stay in the audit log). */
export function useDecide() {
  const qc = useQueryClient();
  const { reviewer } = useReviewer();
  const project = getActiveProject();
  const m = useMutation({
    mutationFn: (v: DecideVars) =>
      post("/api/decide", { ...v, reviewer, ...(project ? { project } : {}) }),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: ["run"] });
      const before = qc.getQueriesData({ queryKey: ["run"] });
      const item = before.map(([, d]) => findItem(d, v.item_id)).find(Boolean);
      const next = v.decision === "reopened" ? (item?.version > 1 ? "edited" : "proposed") : v.decision;
      qc.setQueriesData({ queryKey: ["run"] }, (d: any) => d && patchStatus(d, v.item_id, next));
      const p = item?.payload;
      const name = item?.display_id ?? p?.req_id ?? p?.requirement_id ?? (p?.number ? `§${p.number}` : null)
        ?? v.item_id.split("@")[0];
      return { before, name };
    },
    onError: (e: Error, _v, ctx) => {
      ctx?.before.forEach(([k, d]) => qc.setQueryData(k, d));
      toast.error(e.message);
    },
    onSuccess: (_d, v, ctx) => {
      const text = `${ctx?.name} ${PAST[v.decision]}`;
      announce(text);
      if (v.decision !== "reopened") {
        toast(text, { action: { label: "Undo", onClick: () => m.mutate({ item_id: v.item_id, decision: "reopened" }) } });
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["run"] });
      qc.invalidateQueries({ queryKey: ["audit"] });
    },
  });
  return m;
}

export function useEdit() {
  return useWrite((v: { item_id: string; kind: string; [k: string]: any }, reviewer, project) =>
    post("/api/edit", { ...v, reviewer, ...(project ? { project } : {}) }), { success: () => "Saved as a new version" });
}

export function useAction(runId: string) {
  return useWrite((v: { name: string; [k: string]: any }, reviewer, project) =>
    post(`/api/runs/${runId}/actions/${v.name}`, { ...v, reviewer, ...(project ? { project } : {}) }));
}

export const downloadUrl = (path: string) => `/api/download?path=${encodeURIComponent(path)}`;
