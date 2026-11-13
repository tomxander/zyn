"""Zyn web API and static host. Launch with: python -m harness serve

Read endpoints return view models from views.py. Every write names the reviewer; the audit
store refuses nothing else, so the same rules as the old screen apply: only a named person
decides, AI verdicts are advice, approving over an AI objection needs a reason.

Long stages (model calls) run as background jobs. The screen polls /api/jobs/{id}, which
returns elapsed time and a short trace read from the audit log as the stage writes it.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from harness import PROTOTYPE_LABEL
from harness.api import views
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig
from harness.models.runner import StructuredOutputFailure
from harness.sift import check as sift_check
from harness.sift import pipeline
from harness.sift.rules import list_profiles

WEB_DIST = PROJECT_ROOT / "web" / "dist"
UPLOADS = PROJECT_ROOT / "runs" / "uploads"


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ---- jobs --------------------------------------------------------------------------------

TRACE_TEXT = {
    "ingested": "Read the document", "generated": "Model answered",
    "replayed": "Reused a stored answer (same model, prompt and input)",
    "ai_reviewed": "AI reviewer checked", "ai_batch_done": "AI batch finished",
    "ai_conflicts_done": "Set-wide conflict pass finished",
    "stability_pass_done": "Stability pass finished", "finding_seen": "Finding seen again",
    "finding_corroborated": "Finding corroborated", "fault_checked": "Fault check run",
    "provider_error": "Model call failed, retrying", "ai_review_missed": "Possible miss noted",
    "extracted_none": "No requirements in section", "cases_generated": "Cases generated",
}


class Jobs:
    def __init__(self, audit: AuditStore):
        self.audit = audit
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()

    def start(self, run_id: str | None, label: str, fn: Callable[[], Any]) -> dict:
        job_id = uuid.uuid4().hex[:10]
        last = max((e["event_id"] for e in self.audit.events()), default=0)
        job = {"id": job_id, "run_id": run_id, "label": label, "state": "running",
               "started": time.time(), "ended": None, "after_event": last,
               "result": None, "error": None}
        with self.lock:
            self.jobs[job_id] = job

        def work():
            try:
                job["result"] = _jsonable(fn())
                job["state"] = "done"
            except (StructuredOutputFailure, ValueError, KeyError) as e:
                job["error"], job["state"] = str(e), "failed"
            except Exception as e:  # noqa: BLE001 - reported to the screen, not swallowed
                job["error"], job["state"] = f"{type(e).__name__}: {e}", "failed"
                traceback.print_exc()
            job["ended"] = time.time()

        threading.Thread(target=work, daemon=True).start()
        return self.status(job_id)

    def status(self, job_id: str) -> dict:
        job = self.jobs.get(job_id)
        if not job:
            raise ApiError("Unknown job", 404)
        trace = []
        if job["run_id"]:
            for e in self.audit.events(run_id=job["run_id"]):
                if e["event_id"] > job["after_event"] and e["action"] in TRACE_TEXT:
                    trace.append({"ts": e["ts"], "text": TRACE_TEXT[e["action"]],
                                  "object": e.get("object_id"), "action": e["action"]})
        end = job["ended"] or time.time()
        return {k: job[k] for k in ("id", "run_id", "label", "state", "result", "error")} | {
            "elapsed": round(end - job["started"], 1), "steps": len(trace), "trace": trace[-8:]}


def _jsonable(x: Any) -> Any:
    if hasattr(x, "as_dict"):
        return x.as_dict()
    return json.loads(json.dumps(x, default=str))


# ---- app ---------------------------------------------------------------------------------

def create_app(cfg: HarnessConfig, audit: AuditStore | None = None) -> Starlette:
    audit = audit or AuditStore(cfg.resolved_db_path())
    jobs = Jobs(audit)

    async def body(request: Request) -> dict:
        try:
            return await request.json()
        except json.JSONDecodeError:
            return {}

    def who(data: dict) -> str:
        name = (data.get("reviewer") or "").strip()
        if not name:
            raise ApiError("Enter your name as reviewer first.", 403)
        return name

    def job_response(job: dict) -> JSONResponse:
        return JSONResponse({"job": job}, status_code=202)

    # ---- read ----

    async def config(request: Request):
        from harness.schemas.common import ReqType
        from harness.schemas.sift import Modal, QualityFlag
        return JSONResponse({"label": PROTOTYPE_LABEL, "roles": cfg.roles,
                             "enums": {"req_type": [t.value for t in ReqType],
                                       "modal": [m.value for m in Modal],
                                       "quality_flag": [f.value for f in QualityFlag]},
                             "offline": cfg.is_offline(),
                             "replay": cfg.replay,
                             "knowledge": views.knowledge_view(cfg),
                             "rule_profiles": list_profiles(),
                             "sift_runs": [r["run_id"] for r in audit.list_runs()
                                           if r["workflow"] in views.SIFT]})

    async def runs(request: Request):
        return JSONResponse(views.run_list(audit))

    async def run(request: Request):
        try:
            return JSONResponse(_jsonable(views.run_view(audit, request.path_params["run_id"])))
        except KeyError as e:
            raise ApiError(f"No run {e}", 404) from e

    async def run_audit(request: Request):
        return JSONResponse(_jsonable(views.audit_view(audit, cfg, request.path_params["run_id"])))

    async def job(request: Request):
        return JSONResponse(jobs.status(request.path_params["job_id"]))

    async def download(request: Request):
        path = Path(request.query_params.get("path", "")).resolve()
        if not path.is_file() or (PROJECT_ROOT / "runs") not in path.parents:
            raise ApiError("File not found", 404)
        return FileResponse(path, filename=path.name)

    # ---- item decisions and edits ----

    async def decide(request: Request):
        d = await body(request)
        iid, decision = d.get("item_id", ""), d.get("decision")
        if decision not in ("approved", "rejected", "reopened"):
            raise ApiError("decision must be approved, rejected or reopened")
        item = audit.get_item(iid)
        if not item:
            raise ApiError("No such item", 404)
        comment = (d.get("comment") or "").strip() or None
        if decision == "approved" and audit.status(iid) != "approved":
            if item["item_type"] == "test_spec" and item["payload"].get("problems"):
                raise ApiError("Fails the code checks: edit the spec until they pass.")
            if audit.needs_override_reason(iid) and not comment:
                raise ApiError("The AI reviewer objected. Give a reason for approving.")
        audit.decide(iid, decision, who(d), comment=comment)
        return JSONResponse({"ok": True, "status": audit.status(iid)})

    async def edit(request: Request):
        d = await body(request)
        iid = d.get("item_id", "")
        item = audit.get_item(iid)
        if not item:
            raise ApiError("No such item", 404)
        actor = who(d)
        kind = d.get("kind", "edit")
        p = item["payload"]
        if kind == "apply_suggestion":
            card = views.requirement_card(audit, item)
            if not card["can_apply"]:
                raise ApiError("The AI suggestion cannot be applied with one click.")
            r = card["review"]
            new = {**p}
            if r.get("suggested_text"):
                new["text"] = r["suggested_text"]
            if r.get("suggested_req_type"):
                new["req_type"] = r["suggested_req_type"]
            if r.get("suggested_flags") is not None:
                new["quality_flags"] = r["suggested_flags"]
            audit.edit_item(iid, new, actor, comment="applied AI reviewer suggestion",
                            source="ai_suggestion")
        elif kind == "use_clarification":
            pipeline.apply_clarification(audit, iid, actor)
        elif kind == "revert":
            original = audit.get_item(iid, version=1)["payload"]
            audit.edit_item(iid, original, actor, comment="reverted to the extracted version")
        elif kind == "subsystem":
            new = d["subsystem_id"]
            audit.edit_item(iid, {**p, "subsystem_id": new}, actor,
                            comment=f"subsystem {p['subsystem_id']} -> {new}")
        elif kind == "spec":
            from harness.anvil import pipeline as forge
            new = {**p, **d["fields"]}
            new["problems"] = forge.revalidate(audit, item["run_id"], new)
            audit.edit_item(iid, new, actor, comment=d.get("comment") or None)
        elif kind == "edit":
            allowed = {"text", "req_type", "modal", "quality_flags"}
            new = {**p, **{k: v for k, v in d["fields"].items() if k in allowed}}
            audit.edit_item(iid, new, actor, comment=d.get("comment") or None)
        else:
            raise ApiError(f"Unknown edit kind {kind}")
        return JSONResponse({"ok": True, "version": audit.get_item(iid)["version"]})

    async def bulk(request: Request):
        d = await body(request)
        actor = who(d)
        kind, run_id = d.get("kind"), d.get("run_id")
        view = views.run_view(audit, run_id)
        if kind == "mappings":
            ids, comment = view["bulk_mappings"], "bulk approval, model self-rating >= 0.90"
        elif kind == "requirements":
            ids, comment = (view["bulk_requirements"],
                            "bulk approval: every check passed, AI accepted")
        else:
            raise ApiError("Unknown bulk kind")
        for iid in ids:
            audit.decide(iid, "approved", actor, comment=comment)
        return JSONResponse({"ok": True, "count": len(ids)})

    # ---- stages and other actions ----

    async def action(request: Request):
        d = await body(request)
        actor = who(d)
        run_id, name = request.path_params["run_id"], request.path_params["name"]

        def logged(stage: str, fn):
            def go():
                rep = fn()
                audit.log_event(actor, "stage_started", run_id=run_id,
                                detail={"stage": stage, **_jsonable(rep)})
                return rep
            return go

        if name == "extract":
            return job_response(jobs.start(run_id, "Extracting requirements and running the AI "
                                           "reviewer, section by section",
                                           logged("extract", lambda: pipeline.extract(cfg, audit, run_id))))
        if name == "clarify":
            return job_response(jobs.start(run_id, "Proposing clarifications, section by section",
                                           logged("clarify", lambda: pipeline.clarify(cfg, audit, run_id))))
        if name in ("ai_review", "stability") and views.run_view(audit, run_id).get(
                "ai_available") is False:
            raise ApiError("This run checks tests; the AI reviewer is for requirements.")
        if name == "ai_review":
            return job_response(jobs.start(run_id, "AI reviewer reading the set, batch by batch",
                                           logged("ai_review",
                                                  lambda: sift_check.ai_review(cfg, audit, run_id))))
        if name == "stability":
            total = int(d.get("passes", 3))
            return job_response(jobs.start(run_id, "Repeating the AI review",
                                           logged("stability", lambda: sift_check.stability_check(
                                               cfg, audit, run_id, total))))
        if name == "carry_over":
            return JSONResponse({"count": sift_check.apply_prior(audit, run_id, actor)})
        if name in ("forge_resume", "forge_repropose"):
            from harness.anvil import pipeline as forge
            fn = forge.resume if name == "forge_resume" else forge.repropose
            return job_response(jobs.start(run_id, "Proposing test specs",
                                           lambda: fn(cfg, audit, run_id)))
        if name == "forge_generate":
            from harness.anvil import pipeline as forge
            return JSONResponse(_jsonable(forge.generate(audit, run_id, actor)))
        if name == "mark_stale":
            from harness.anvil import impact as fimpact
            return JSONResponse({"count": fimpact.mark_stale(audit, run_id, actor)})
        if name == "update_requirement":
            from harness.anvil import impact as fimpact
            entry = audit.get_item(d["entry_id"])
            fimpact.update_requirement(audit, d["requirement_item"], d["text"].strip(),
                                       entry["payload"], actor, run_id)
            return JSONResponse({"ok": True})
        if name == "evidence":
            from harness.evidence import export_evidence
            return JSONResponse(_jsonable(export_evidence(audit, run_id, actor, cfg)))
        if name == "export":
            wf = views.run_view(audit, run_id)["kind"]
            if wf in ("sift", "smoke"):
                from harness.sift.export import export
                res = export(audit, run_id, actor)
            elif wf == "check":
                res = sift_check.export_findings(audit, run_id, actor)
            elif wf == "forge":
                from harness.anvil import pipeline as forge
                res = forge.export(audit, run_id, actor)
            else:
                from harness.sift import delta as sift_delta
                res = sift_delta.export_delta(audit, run_id, actor)
            return JSONResponse(_jsonable(res))
        if name == "score":
            key = Path(d.get("key_path") or "")
            key = key if key.is_absolute() else PROJECT_ROOT / key
            if not key.is_file():
                raise ApiError("Answer key file not found")
            kind = views.run_view(audit, run_id)["kind"]
            if kind == "delta":
                from harness.sift import delta as sift_delta
                return JSONResponse({"rows": [{"label": "Expected changes",
                                               **sift_delta.score(audit, run_id, key)}]})
            rows_ = [("Code checks only", ("code",), 1), ("AI reviewer only", ("ai",), 1),
                     ("Code and AI together", ("code", "ai"), 1)]
            n_pass = len(sift_check.passes_done(audit, run_id))
            if n_pass > 1:
                rows_.append((f"Code and AI, AI findings seen in all {n_pass} passes",
                              ("code", "ai"), n_pass))
            return JSONResponse({"rows": [
                {"label": lbl, **sift_check.score(audit, run_id, key, srcs, min_passes=mp)}
                for lbl, srcs, mp in rows_]})
        raise ApiError(f"Unknown action {name}", 404)

    # ---- new runs ----

    async def new_run(request: Request):
        form = await request.form()
        who({"reviewer": form.get("reviewer")})  # a named person starts every run
        kind = request.path_params["kind"]
        UPLOADS.mkdir(parents=True, exist_ok=True)

        async def save(field: str) -> Path | None:
            up = form.get(field)
            if not up or not getattr(up, "filename", ""):
                return None
            dest = UPLOADS / Path(up.filename).name
            dest.write_bytes(await up.read())
            return dest

        if kind == "sift":
            path = await save("file")
            if not path:
                raise ApiError("Choose a specification file.")
            return job_response(jobs.start(None, "Reading the document and mapping sections",
                                           lambda: pipeline.start(cfg, audit, path)))
        if kind == "check":
            path = await save("file")
            if not path:
                raise ApiError("Choose a requirement set.")
            style = "ears" if form.get("ears") == "true" else None
            source = await save("source")
            try:
                rep = sift_check.start(cfg, audit, path, style=style,
                                       rules=form.get("rules") or None, source=source)
            except (FileNotFoundError, ValueError) as e:
                raise ApiError(str(e)) from e
            return JSONResponse(_jsonable(rep))
        if kind == "tests":
            from harness.outside import start_tests
            tests = await save("file")
            if not tests:
                raise ApiError("Choose a test file.")
            dbc = await save("dbc") or PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"
            reqs = await save("reqs")
            try:
                run_id = start_tests(audit, [tests], dbc, reqs)
            except (ValueError, OSError) as e:
                raise ApiError(str(e)) from e
            return JSONResponse({"run_id": run_id})
        if kind == "delta":
            from harness.sift import delta as sift_delta
            new = await save("new")
            if form.get("mode") == "spec":
                if not (new and form.get("base")):
                    raise ApiError("Choose the approved Sift run and the new revision.")
                rep = sift_delta.spec_delta(cfg, audit, form["base"], new)
            else:
                old = await save("old")
                if not (old and new):
                    raise ApiError("Choose both requirement sets.")
                rep = sift_delta.set_delta(cfg, audit, old, new)
            return JSONResponse(_jsonable(rep))
        if kind == "forge":
            from harness.anvil import pipeline as forge
            dbc = await save("dbc") or PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"
            base = form.get("base")
            if not base:
                raise ApiError("Choose an approved Sift run.")
            return job_response(jobs.start(None, "Proposing a test template for each approved "
                                           "requirement", lambda: forge.start(cfg, audit, base, dbc)))
        raise ApiError(f"Unknown run kind {kind}", 404)

    async def on_error(request: Request, exc: Exception):
        if isinstance(exc, ApiError):
            return JSONResponse({"error": str(exc)}, status_code=exc.status)
        if isinstance(exc, (ValueError, StructuredOutputFailure)):
            return JSONResponse({"error": str(exc)}, status_code=400)
        traceback.print_exc()
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)

    async def index(request: Request):
        # files at the root of the built screen (the favicon) are served as themselves
        name = request.path_params.get("path", "")
        root_file = (WEB_DIST / name).resolve()
        if name and "/" not in name and root_file.parent == WEB_DIST.resolve() and root_file.is_file():
            return FileResponse(root_file)
        page = WEB_DIST / "index.html"
        if not page.is_file():
            return Response("Web screen not built. Run: cd web; npm run build", status_code=503)
        return FileResponse(page)

    routes = [
        Route("/api/config", config),
        Route("/api/runs", runs),
        Route("/api/runs/{run_id}", run),
        Route("/api/runs/{run_id}/audit", run_audit),
        Route("/api/runs/{run_id}/actions/{name}", action, methods=["POST"]),
        Route("/api/new/{kind}", new_run, methods=["POST"]),
        Route("/api/jobs/{job_id}", job),
        Route("/api/decide", decide, methods=["POST"]),
        Route("/api/edit", edit, methods=["POST"]),
        Route("/api/bulk", bulk, methods=["POST"]),
        Route("/api/download", download),
    ]
    if (WEB_DIST / "assets").is_dir():
        routes.append(Mount("/assets", StaticFiles(directory=WEB_DIST / "assets")))
    routes.append(Route("/{path:path}", index))
    handlers = {ApiError: on_error, ValueError: on_error, KeyError: on_error,
                StructuredOutputFailure: on_error, Exception: on_error}
    return Starlette(routes=routes, exception_handlers=handlers)
