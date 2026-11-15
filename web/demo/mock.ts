// The online demo's stand-in for the Zyn API. The review screen runs unchanged; this answers its
// /api calls from runs recorded from the real API (synthetic ICX-100 data, reviewer names replaced)
// and applies decisions in memory. Nothing is stored or sent anywhere: a reload starts fresh.

import config from "./fixtures/config.json";
import runs from "./fixtures/runs.json";
import actions from "./fixtures/actions.json";

const views = import.meta.glob("./fixtures/run-*.json", { eager: true, import: "default" }) as Record<string, any>;
const audits = import.meta.glob("./fixtures/audit-*.json", { eager: true, import: "default" }) as Record<string, any>;

const BASE = import.meta.env.BASE_URL; // e.g. /zyn/demo/
const NEEDS_APP = "Not in the online demo: this needs Zyn running on your machine. Decisions and exports work here.";

const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));
const byRun = (all: Record<string, any>, prefix: string) => {
  const out: Record<string, any> = {};
  for (const [path, data] of Object.entries(all)) out[path.split(`${prefix}-`)[1].replace(".json", "")] = clone(data);
  return out;
};
const state = { views: byRun(views, "run"), audits: byRun(audits, "audit"), nextEvent: 100000 };

const FINDING_STATE: Record<string, string> = { proposed: "open", edited: "open", approved: "confirmed", rejected: "dismissed" };
const DELTA_STATE: Record<string, string> = { proposed: "open", edited: "open", approved: "needs action", rejected: "no action" };

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const fail = (error: string, status = 400) => json({ error }, status);

/** Every object in a view that carries this item id (the same item can appear in two lists). */
function holders(o: any, id: string, out: any[] = []): any[] {
  if (Array.isArray(o)) o.forEach((x) => holders(x, id, out));
  else if (o && typeof o === "object") {
    if (o.item_id === id && "status" in o) out.push(o);
    for (const v of Object.values(o)) if (v && typeof v === "object") holders(v, id, out);
  }
  return out;
}

/** Counts the screen shows next to the items, recomputed the way the server does. */
function recount(v: any) {
  if (v.kind === "check" && Array.isArray(v.requirements) && Array.isArray(v.findings)) {
    for (const r of v.requirements)
      r.open = v.findings.filter((f: any) => f.payload?.req_id === r.id && f.state === "open").length;
  }
  if (v.kind === "forge" && v.spec_counts && Array.isArray(v.specs)) {
    for (const k of Object.keys(v.spec_counts)) v.spec_counts[k] = v.specs.filter((s: any) => s.status === k).length;
  }
}

function logEvent(runId: string, actor: string, action: string, objectId: string, comment?: string) {
  const a = state.audits[runId];
  if (!a?.events) return;
  a.events.push({
    event_id: state.nextEvent++, ts: new Date().toISOString(), actor, action, object_id: objectId, object_version: 1,
    model_served: null, tokens_in: null, tokens_out: null, latency_ms: null, attempt: null,
    ...(comment ? { comment } : {}),
  });
}

function decide(body: any) {
  const { item_id: id, decision, comment, reviewer } = body ?? {};
  if (!["approved", "rejected", "reopened"].includes(decision)) return fail("decision must be approved, rejected or reopened");
  if (!String(reviewer ?? "").trim()) return fail("Enter your name as reviewer first.");
  const runId = String(id).split("@")[1];
  const v = state.views[runId];
  const found = v ? holders(v, id) : [];
  if (!found.length) return fail("No such item", 404);
  const item = found[0];
  const d = item.decision ?? {};
  // The same rules the server enforces; the recorded view already says which apply.
  if (d.block_decide) return fail(d.block_decide);
  if (decision === "approved" && item.status !== "approved") {
    if (d.block_approve) return fail(d.block_approve);
    if (d.needs_reason && !String(comment ?? "").trim()) return fail("The AI reviewer objected. Give a reason for approving.");
  }
  const status = decision === "reopened" ? "proposed" : decision;
  const map = v.kind === "delta" ? DELTA_STATE : FINDING_STATE;
  for (const h of found) {
    h.status = status;
    if ("state" in h && typeof h.state === "string" && map[status]) h.state = map[status];
    if (h.decision && typeof h.decision === "object") h.decision.status = status;
  }
  recount(v);
  logEvent(runId, String(reviewer).trim(), decision, id, comment);
  return json({ ok: true, status });
}

/** Export and evidence hand back the real files made from these runs, bundled with the demo. */
function action(runId: string, name: string) {
  const rec = (actions as Record<string, any>)[`${runId}:${name}`];
  if (!rec) return fail(NEEDS_APP);
  const out = clone(rec);
  const files: Record<string, string> = {};
  for (const [k, p] of Object.entries(out.files ?? {})) files[k] = demoFile(String(p));
  out.files = files;
  return json(out);
}

/** A recorded export path becomes a path inside the demo's own files folder. */
export function demoFile(p: string) {
  const m = p.replace(/\\/g, "/").match(/exports\/(.+)$/);
  return m ? `demo-files/${m[1]}` : p;
}

async function route(url: URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method || "GET").toUpperCase();
  const body = init?.body ? JSON.parse(String(init.body)) : undefined;
  const p = url.pathname.replace(BASE.replace(/\/$/, ""), "");
  let m: RegExpMatchArray | null;

  if (method === "GET" && p === "/api/config") return json(config);
  if (method === "GET" && p === "/api/runs") return json(runs);
  if (method === "GET" && (m = p.match(/^\/api\/runs\/([^/]+)\/audit$/))) {
    const a = state.audits[m[1]];
    return a ? json(a) : fail(`No run ${m[1]}`, 404);
  }
  if (method === "GET" && (m = p.match(/^\/api\/runs\/([^/]+)$/))) {
    const v = state.views[m[1]];
    return v ? json(v) : fail(`No run ${m[1]}`, 404);
  }
  if (method === "POST" && p === "/api/decide") return decide(body);
  if (method === "POST" && (m = p.match(/^\/api\/runs\/([^/]+)\/actions\/([^/]+)$/))) return action(m[1], m[2]);
  if (method === "POST") return fail(NEEDS_APP);
  return fail("Not in the online demo.", 404);
}

/** Answers the app's /api calls; everything else (scripts, fonts) goes to the network as usual. */
export function installMock() {
  const real = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, location.href);
    if (url.origin === location.origin && /\/api\//.test(url.pathname) && !url.pathname.includes("/api/download")) {
      await new Promise((r) => setTimeout(r, 120)); // a little latency, so loading states show as they would
      return route(url, init);
    }
    return real(input, init);
  };
  // Download links point at /api/download?path=...; in the demo they open the bundled file instead.
  document.addEventListener(
    "click",
    (e) => {
      const a = (e.target as Element).closest?.("a");
      if (!a) return;
      const href = a.getAttribute("href") || "";
      if (!href.includes("/api/download")) return;
      const path = new URL(href, location.href).searchParams.get("path") || "";
      a.setAttribute("href", `${BASE}${demoFile(path)}`);
    },
    true,
  );
  try {
    if (!localStorage.getItem("zyn.reviewer")) localStorage.setItem("zyn.reviewer", "Demo visitor");
  } catch {
    /* private mode: the screen asks for a name instead */
  }
}
