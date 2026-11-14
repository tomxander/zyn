"""Zyn web API and static host. Launch with: python -m harness serve

Read endpoints return view models from views.py. Every write names the reviewer; the audit
store refuses nothing else, so the same rules as the old screen apply: only a named person
decides, AI verdicts are advice, approving over an AI objection needs a reason.

Long stages (model calls) run as background jobs. The screen polls /api/jobs/{id}, which
returns elapsed time and a short trace read from the audit log as the stage writes it.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from harness import PROTOTYPE_LABEL
from harness.api import views
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, HarnessConfig, web_dist
from harness.models.runner import StructuredOutputFailure
from harness.sift import check as sift_check
from harness.sift import pipeline
from harness.sift.rules import list_profiles
from harness.team.auth import IdentityProvider, OidcProvider
from harness.team.permissions import Access, Verdict, access_for_groups, can, can_decide
from harness.team.principal import Principal
from harness.team.tokens import resolve_token

WEB_DIST = web_dist()
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

    def start(
        self,
        run_id: str | None,
        label: str,
        fn: Callable[[], Any],
        project: str | None = None,
        principal_id: str | None = None,
    ) -> dict:
        job_id = uuid.uuid4().hex[:10]
        last = max((e["event_id"] for e in self.audit.events()), default=0)
        job = {
            "id": job_id,
            "run_id": run_id,
            "project": project,
            "principal_id": principal_id,
            "label": label,
            "state": "running",
            "started": time.time(),
            "ended": None,
            "after_event": last,
            "result": None,
            "error": None,
        }
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

def create_app(
    cfg: HarnessConfig,
    audit: AuditStore | None = None,
    idp: IdentityProvider | None = None,
    fake_sign_in: tuple[str, list[str]] | None = None,
) -> Starlette:
    db_target = (
        cfg.team.database_url
        if cfg.is_team() and cfg.team and cfg.team.database_url
        else cfg.resolved_db_path()
    )
    audit = audit or AuditStore(db_target)
    if cfg.is_team():
        from harness.audit.migrations import LATEST_VERSION, current_version

        cur_ver = current_version(audit.backend)
        if cur_ver < LATEST_VERSION:
            raise RuntimeError(
                f"Database schema is version {cur_ver}, this Zyn needs {LATEST_VERSION}. Run: zyn upgrade"
            )
    jobs = Jobs(audit)
    if cfg.is_team() and fake_sign_in:
        from harness.team.auth import Claims, FakeIdentityProvider

        name, groups = fake_sign_in
        claims: Claims = {
            "sub": f"user-{name.lower()}",
            "iss": "https://idp",
            "name": name,
            "email": f"{name.lower()}@example.com",
            "groups": groups,
        }
        idp = FakeIdentityProvider(claims)
    elif cfg.is_team() and idp is None:
        assert cfg.team is not None
        idp = OidcProvider(cfg.team.oidc, cfg.team.public_url)

    async def body(request: Request) -> dict:
        try:
            return await request.json()
        except json.JSONDecodeError:
            return {}

    def resolve_request_access(request: Request) -> Access:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            assert cfg.team is not None
            access = resolve_token(audit, cfg.team, token)
            if not access:
                raise ApiError("Sign in first.", 401)
            return access

        session = request.session if hasattr(request, "session") else {}
        p_data = session.get("principal")
        if not p_data:
            raise ApiError("Sign in first.", 401)

        if (
            request.method in ("POST", "PUT", "DELETE", "PATCH")
            and request.headers.get("X-Zyn-Request") != "1"
        ):
            raise ApiError("Missing X-Zyn-Request header.", 403)

        principal = Principal(**p_data)
        sid = session.get("sid")
        if not sid:
            session.clear()
            raise ApiError("Sign in first.", 401)
        signed_in_at = session.get("signed_in_at", "")

        def _parse_ts(ts_str: str) -> datetime:
            try:
                return datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                return datetime.min.replace(tzinfo=UTC)

        signed_dt = _parse_ts(signed_in_at)
        assert cfg.team is not None
        if datetime.now(UTC) - signed_dt > timedelta(hours=cfg.team.session_hours):
            session.clear()
            raise ApiError("Sign in first.", 401)
        with audit.backend.connect() as con:
            s_out = con.execute(
                "SELECT event_id FROM events WHERE action = 'signed_out' AND object_id = ? LIMIT 1",
                (sid,),
            )
            if s_out:
                session.clear()
                raise ApiError("Sign in first.", 401)

            p_rev = con.execute(
                "SELECT ts FROM events WHERE action = 'person_revoked' AND (object_id = ? OR actor_id = ?) ORDER BY event_id DESC",
                (principal.id, principal.id),
            )
            for r in p_rev:
                if _parse_ts(r["ts"]) > signed_dt:
                    session.clear()
                    raise ApiError("Sign in first.", 401)
            p_legacy = con.execute(
                "SELECT ts, detail_json FROM events WHERE action = 'person_revoked' AND object_id IS NULL AND actor_id IS NULL"
            )
            for r in p_legacy:
                dtl = json.loads(r["detail_json"]) if r["detail_json"] else {}
                if dtl.get("person_id") == principal.id and _parse_ts(r["ts"]) > signed_dt:
                    session.clear()
                    raise ApiError("Sign in first.", 401)

            s_rows = con.execute(
                "SELECT detail_json FROM events WHERE action = 'signed_in' AND actor_id = ? ORDER BY event_id DESC LIMIT 1",
                (principal.id,),
            )
            groups = []
            if s_rows and s_rows[0]["detail_json"]:
                dtl = json.loads(s_rows[0]["detail_json"])
                groups = dtl.get("groups", [])
        assert cfg.team is not None
        return access_for_groups(principal, groups, cfg.team)

    def who(request: Request, data: dict) -> Access:
        if not cfg.is_team():
            name = (data.get("reviewer") or "").strip()
            if not name:
                raise ApiError("Enter your name as reviewer first.", 403)
            return Access(
                Principal(id="", name=name, email=None, kind="typed"),
                {},
                admin=True,
            )
        return getattr(request.state, "access", None) or resolve_request_access(request)

    def job_response(job: dict) -> JSONResponse:
        return JSONResponse({"job": job}, status_code=202)

    async def access_log_middleware(request: Request, call_next: Callable):
        start = time.perf_counter()
        res = await call_next(request)
        if cfg.is_team() and request.url.path.startswith(("/api", "/auth")):
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            access = getattr(request.state, "access", None)
            principal_id = access.principal.id if access else None
            project = request.query_params.get("project") or getattr(request.state, "project", None)
            log_entry = {
                "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "method": request.method,
                "path": request.url.path,
                "status": res.status_code,
                "duration_ms": duration_ms,
                "principal_id": principal_id,
                "project": project,
            }
            print(json.dumps(log_entry), file=sys.stderr, flush=True)
        return res

    async def auth_gate(request: Request, call_next: Callable):
        path = request.url.path
        if cfg.is_team() and path.startswith("/api/") and path != "/api/health":
            try:
                access = resolve_request_access(request)
                request.state.access = access
            except ApiError as e:
                return JSONResponse({"error": str(e)}, status_code=e.status)
        return await call_next(request)

    async def health(request: Request) -> JSONResponse:
        from harness import __version__
        from harness.audit.migrations import current_version

        return JSONResponse({
            "status": "ok",
            "version": __version__,
            "mode": "team" if cfg.is_team() else "personal",
            "schema": current_version(audit.backend),
        })

    async def auth_login(request: Request) -> Response:
        if not cfg.is_team() or idp is None:
            raise ApiError("Team mode not enabled", 400)
        return await idp.login_redirect(request)

    async def auth_callback(request: Request) -> Response:
        effective_idp = getattr(request.app.state, "idp", idp)
        if not cfg.is_team() or effective_idp is None:
            raise ApiError("Team mode not enabled", 400)
        claims = await effective_idp.callback(request)
        principal = Principal(
            id=f"oidc:{claims['iss']}#{claims['sub']}",
            name=claims.get("name") or claims["sub"],
            email=claims.get("email"),
            kind="person",
        )
        audit.log_event(
            actor=principal.name,
            action="signed_in",
            actor_id=principal.id,
            detail={"groups": claims.get("groups", [])},
        )
        if hasattr(request, "session"):
            request.session["sid"] = uuid.uuid4().hex
            request.session["principal"] = {
                "id": principal.id,
                "name": principal.name,
                "email": principal.email,
                "kind": principal.kind,
            }
            request.session["signed_in_at"] = datetime.now(UTC).isoformat(timespec="milliseconds")
        return RedirectResponse("/", status_code=303)

    async def auth_logout(request: Request) -> Response:
        if request.method != "POST":
            raise ApiError("Logout must be a POST request.", 405)
        if request.headers.get("X-Zyn-Request") != "1":
            raise ApiError("Missing X-Zyn-Request header.", 403)
        if hasattr(request, "session") and request.session.get("principal"):
            p_data = request.session.get("principal", {})
            sid = request.session.get("sid", "")
            audit.log_event(
                actor=p_data.get("name", ""),
                action="signed_out",
                actor_id=p_data.get("id"),
                object_id=sid,
                detail={"session_id": sid, "person_id": p_data.get("id")},
            )
            request.session.clear()
        return JSONResponse({"status": "ok"})

    # ---- read ----

    async def config(request: Request):
        from harness import __version__
        from harness.schemas.common import ReqType
        from harness.schemas.sift import Modal, QualityFlag

        base_resp = {
            "label": PROTOTYPE_LABEL,
            "version": __version__,
            "roles": cfg.roles,
            "enums": {
                "req_type": [t.value for t in ReqType],
                "modal": [m.value for m in Modal],
                "quality_flag": [f.value for f in QualityFlag],
            },
            "offline": cfg.is_offline(),
            "replay": cfg.replay,
            "knowledge": views.knowledge_view(cfg),
            "rule_profiles": list_profiles(),
            "sift_runs": [
                r["run_id"]
                for r in audit.list_runs()
                if r["workflow"] in views.SIFT
            ],
            "mode": "team" if cfg.is_team() else "personal",
        }
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            projects_list = []
            assert cfg.team is not None
            if access.admin:
                for pid, ps in cfg.team.projects.items():
                    projects_list.append({
                        "id": pid,
                        "name": ps.name,
                        "role": access.roles.get(pid),
                        "four_eyes": ps.four_eyes,
                    })
            else:
                for pid, role in access.roles.items():
                    ps = cfg.team.projects.get(pid)
                    if ps:
                        projects_list.append({
                            "id": pid,
                            "name": ps.name,
                            "role": role,
                            "four_eyes": ps.four_eyes,
                        })
            base_resp["person"] = {
                "name": access.principal.name,
                "email": access.principal.email,
            }
            base_resp["projects"] = projects_list
            base_resp["admin"] = access.admin
            req_project = request.query_params.get("project")
            if not req_project:
                if access.roles:
                    req_project = next(iter(access.roles.keys()))
                elif access.admin and cfg.team.projects:
                    req_project = next(iter(cfg.team.projects.keys()))
            if req_project and (
                req_project not in cfg.team.projects
                or (req_project not in access.roles and not access.admin)
            ):
                req_project = None
            base_resp["project"] = req_project

            allowed_projects = (
                {req_project}
                if req_project
                else (set(cfg.team.projects.keys()) if access.admin else set(access.roles.keys()))
            )
            base_resp["sift_runs"] = [
                r["run_id"]
                for r in audit.list_runs()
                if r["workflow"] in views.SIFT and r.get("project") in allowed_projects
            ]
        else:
            base_resp["person"] = None
            base_resp["projects"] = []
            base_resp["admin"] = True
            base_resp["project"] = None
        return JSONResponse(base_resp)

    async def runs(request: Request):
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            project = request.query_params.get("project")
            if not project and access.roles:
                project = next(iter(access.roles.keys()))
            if not project or (project not in access.roles and not access.admin):
                return JSONResponse([])
            scoped = audit.scoped(project, access.principal)
            return JSONResponse(views.run_list(scoped))
        return JSONResponse(views.run_list(audit))

    async def run(request: Request):
        run_id = request.path_params["run_id"]
        try:
            if cfg.is_team():
                access = getattr(request.state, "access", None) or resolve_request_access(request)
                proj = audit.run_project(run_id)
                if not proj or (proj not in access.roles and not access.admin):
                    raise ApiError(f"No run {run_id}", 404)
                scoped = audit.scoped(proj, access.principal)

                def rights(item: dict) -> Verdict:
                    assert cfg.team is not None
                    return can_decide(access, item, audit, cfg.team)

                return JSONResponse(_jsonable(views.run_view(scoped, run_id, rights=rights)))
            return JSONResponse(_jsonable(views.run_view(audit, run_id)))
        except KeyError as e:
            raise ApiError(f"No run {e}", 404) from e

    async def run_audit(request: Request):
        run_id = request.path_params["run_id"]
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = audit.run_project(run_id)
            request.state.project = proj
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError(f"No run {run_id}", 404)
            scoped = audit.scoped(proj, access.principal)
            return JSONResponse(_jsonable(views.audit_view(scoped, cfg, run_id)))
        return JSONResponse(_jsonable(views.audit_view(audit, cfg, run_id)))

    async def job(request: Request):
        job_id = request.path_params["job_id"]
        job_info = jobs.jobs.get(job_id)
        if not job_info:
            raise ApiError("Unknown job", 404)
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            job_proj = job_info.get("project")
            if not job_proj and job_info.get("run_id"):
                job_proj = audit.run_project(job_info["run_id"])
            if job_proj and (job_proj not in access.roles and not access.admin):
                raise ApiError("Unknown job", 404)
            if not job_proj and not access.admin:
                raise ApiError("Unknown job", 404)
        return JSONResponse(jobs.status(job_id))

    async def download(request: Request):
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            run_id = request.query_params.get("run_id")
            if not run_id:
                raise ApiError("File not found", 404)
            proj = audit.run_project(run_id)
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError("File not found", 404)
            rel_path = request.query_params.get("path", "")
            export_dir = (PROJECT_ROOT / "runs" / "exports" / run_id).resolve()
            target = (export_dir / rel_path).resolve()
            if not target.is_file() or (
                export_dir not in target.parents and export_dir != target.parent
            ):
                raise ApiError("File not found", 404)
            return FileResponse(target, filename=target.name)

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

        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = audit.run_project(item["run_id"])
            request.state.project = proj
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError("No such item", 404)
            assert cfg.team is not None
            v = can_decide(access, item, audit, cfg.team)
            if not v.ok:
                raise ApiError(v.reason, 403)
            proj_cfg = cfg.team.projects.get(proj)
            four_eyes = proj_cfg.four_eyes if proj_cfg else True
            target_audit = audit.scoped(proj, access.principal)
            actor = access.principal.name
        else:
            who_acc = who(request, d)
            target_audit = audit
            actor = who_acc.principal.name
            four_eyes = False

        comment = (d.get("comment") or "").strip() or None
        if decision == "approved" and target_audit.status(iid) != "approved":
            if item["item_type"] == "test_spec" and item["payload"].get("problems"):
                raise ApiError("Fails the code checks: edit the spec until they pass.")
            if target_audit.needs_override_reason(iid) and not comment:
                raise ApiError("The AI reviewer objected. Give a reason for approving.")

        extra = {"four_eyes": four_eyes} if cfg.is_team() else {}
        target_audit.decide(
            iid,
            decision,
            actor,
            comment=comment,
            extra=extra,
        )
        return JSONResponse({"ok": True, "status": target_audit.status(iid)})

    async def edit(request: Request):
        d = await body(request)
        iid = d.get("item_id", "")
        item = audit.get_item(iid)
        if not item:
            raise ApiError("No such item", 404)

        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = audit.run_project(item["run_id"])
            request.state.project = proj
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError("No such item", 404)
            v = can(access, proj, "edit")
            if not v.ok:
                raise ApiError(v.reason, 403)
            actor = access.principal.name
            target_store = audit.scoped(proj, access.principal)
        else:
            actor = who(request, d).principal.name
            target_store = audit

        kind = d.get("kind", "edit")
        p = item["payload"]
        if kind == "apply_suggestion":
            card = views.requirement_card(target_store, item)
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
            target_store.edit_item(
                iid,
                new,
                actor,
                comment="applied AI reviewer suggestion",
                source="ai_suggestion",
            )
        elif kind == "use_clarification":
            pipeline.apply_clarification(target_store, iid, actor)
        elif kind == "revert":
            original = target_store.get_item(iid, version=1)["payload"]
            target_store.edit_item(
                iid, original, actor, comment="reverted to the extracted version"
            )
        elif kind == "subsystem":
            new = d["subsystem_id"]
            target_store.edit_item(
                iid,
                {**p, "subsystem_id": new},
                actor,
                comment=f"subsystem {p['subsystem_id']} -> {new}",
            )
        elif kind == "spec":
            from harness.anvil import pipeline as forge

            new = {**p, **d["fields"]}
            new["problems"] = forge.revalidate(target_store, item["run_id"], new)
            target_store.edit_item(iid, new, actor, comment=d.get("comment") or None)
        elif kind == "edit":
            allowed = {"text", "req_type", "modal", "quality_flags"}
            new = {**p, **{k: v for k, v in d["fields"].items() if k in allowed}}
            target_store.edit_item(iid, new, actor, comment=d.get("comment") or None)
        else:
            raise ApiError(f"Unknown edit kind {kind}")
        return JSONResponse({"ok": True, "version": target_store.get_item(iid)["version"]})

    async def bulk(request: Request):
        d = await body(request)
        kind, run_id = d.get("kind"), d.get("run_id")
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = audit.run_project(run_id)
            request.state.project = proj
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError(f"No run {run_id}", 404)
            scoped = audit.scoped(proj, access.principal)
            proj_cfg = cfg.team.projects.get(proj)
            four_eyes = proj_cfg.four_eyes if proj_cfg else True
            view = views.run_view(scoped, run_id)
            if kind == "mappings":
                ids, comment = view["bulk_mappings"], "bulk approval, model self-rating >= 0.90"
            elif kind == "requirements":
                ids, comment = (
                    view["bulk_requirements"],
                    "bulk approval: every check passed, AI accepted",
                )
            else:
                raise ApiError("Unknown bulk kind")
            approved_count = 0
            skipped = []
            assert cfg.team is not None
            for iid in ids:
                item = audit.get_item(iid)
                if not item:
                    continue
                v = can_decide(access, item, audit, cfg.team)
                if not v.ok:
                    skipped.append({"item_id": iid, "reason": v.reason})
                    continue
                scoped.decide(
                    iid,
                    "approved",
                    access.principal.name,
                    comment=comment,
                    extra={"four_eyes": four_eyes},
                )
                approved_count += 1
            return JSONResponse({"ok": True, "count": approved_count, "skipped": skipped})

        actor = who(request, d).principal.name
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
        return JSONResponse({"ok": True, "count": len(ids), "skipped": []})

    # ---- stages and other actions ----

    async def action(request: Request):
        d = await body(request)
        run_id, name = request.path_params["run_id"], request.path_params["name"]
        if cfg.is_team():
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = audit.run_project(run_id)
            request.state.project = proj
            if not proj or (proj not in access.roles and not access.admin):
                raise ApiError(f"No run {run_id}", 404)
            v = can(access, proj, "run")
            if not v.ok:
                raise ApiError(v.reason, 403)
            actor = access.principal.name
            target_audit = audit.scoped(proj, access.principal)
        else:
            actor = who(request, d).principal.name
            target_audit = audit

        def logged(stage: str, fn):
            def go():
                rep = fn()
                target_audit.log_event(
                    actor,
                    "stage_started",
                    run_id=run_id,
                    detail={"stage": stage, **_jsonable(rep)},
                )
                return rep

            return go

        if name == "extract":
            return job_response(
                jobs.start(
                    run_id,
                    "Extracting requirements and running the AI reviewer, section by section",
                    logged("extract", lambda: pipeline.extract(cfg, target_audit, run_id)),
                    project=proj if cfg.is_team() else None,
                    principal_id=access.principal.id if cfg.is_team() else None,
                )
            )
        if name == "clarify":
            return job_response(
                jobs.start(
                    run_id,
                    "Proposing clarifications, section by section",
                    logged("clarify", lambda: pipeline.clarify(cfg, target_audit, run_id)),
                    project=proj if cfg.is_team() else None,
                    principal_id=access.principal.id if cfg.is_team() else None,
                )
            )
        if (
            name in ("ai_review", "stability")
            and views.run_view(target_audit, run_id).get("ai_available") is False
        ):
            raise ApiError("This run checks tests; the AI reviewer is for requirements.")
        if name == "ai_review":
            return job_response(
                jobs.start(
                    run_id,
                    "AI reviewer reading the set, batch by batch",
                    logged(
                        "ai_review",
                        lambda: sift_check.ai_review(cfg, target_audit, run_id),
                    ),
                    project=proj if cfg.is_team() else None,
                    principal_id=access.principal.id if cfg.is_team() else None,
                )
            )
        if name == "stability":
            total = int(d.get("passes", 3))
            return job_response(
                jobs.start(
                    run_id,
                    "Repeating the AI review",
                    logged(
                        "stability",
                        lambda: sift_check.stability_check(
                            cfg, target_audit, run_id, total
                        ),
                    ),
                    project=proj if cfg.is_team() else None,
                    principal_id=access.principal.id if cfg.is_team() else None,
                )
            )
        if name == "carry_over":
            if cfg.is_team():
                candidates = sift_check.carry_over_candidates(target_audit, run_id)
                proj_cfg = cfg.team.projects.get(proj)
                four_eyes = proj_cfg.four_eyes if proj_cfg else True
                approved_count = 0
                skipped = []
                assert cfg.team is not None
                for f in candidates:
                    v = can_decide(access, f, audit, cfg.team)
                    if not v.ok:
                        skipped.append({"item_id": f["item_id"], "reason": v.reason})
                        continue
                    p = f["payload"]["prior"]
                    comment = (
                        f"carried over: {p['decision']} by {p['by']} in run {p['run_id']}"
                        + (f" ({p['comment']})" if p.get("comment") else "")
                    )
                    target_audit.decide(
                        f["item_id"],
                        p["decision"],
                        actor,
                        comment=comment,
                        extra={"four_eyes": four_eyes},
                    )
                    approved_count += 1
                return JSONResponse({"count": approved_count, "skipped": skipped})
            return JSONResponse({"count": sift_check.apply_prior(target_audit, run_id, actor)})
        if name in ("forge_resume", "forge_repropose"):
            from harness.anvil import pipeline as forge

            fn = forge.resume if name == "forge_resume" else forge.repropose
            return job_response(
                jobs.start(
                    run_id,
                    "Proposing test specs",
                    lambda: fn(cfg, target_audit, run_id),
                    project=proj if cfg.is_team() else None,
                    principal_id=access.principal.id if cfg.is_team() else None,
                )
            )
        if name == "forge_generate":
            from harness.anvil import pipeline as forge

            return JSONResponse(_jsonable(forge.generate(target_audit, run_id, actor)))
        if name == "mark_stale":
            from harness.anvil import impact as fimpact

            return JSONResponse({"count": fimpact.mark_stale(target_audit, run_id, actor)})
        if name == "update_requirement":
            from harness.anvil import impact as fimpact

            entry = target_audit.get_item(d["entry_id"])
            fimpact.update_requirement(
                target_audit,
                d["requirement_item"],
                d["text"].strip(),
                entry["payload"],
                actor,
                run_id,
            )
            return JSONResponse({"ok": True})
        if name == "evidence":
            from harness.evidence import export_evidence

            return JSONResponse(_jsonable(export_evidence(target_audit, run_id, actor, cfg)))
        if name == "export":
            wf = views.run_view(target_audit, run_id)["kind"]
            if wf in ("sift", "smoke"):
                from harness.sift.export import export

                res = export(target_audit, run_id, actor)
            elif wf == "check":
                res = sift_check.export_findings(target_audit, run_id, actor)
            elif wf == "forge":
                from harness.anvil import pipeline as forge

                res = forge.export(target_audit, run_id, actor)
            else:
                from harness.sift import delta as sift_delta

                res = sift_delta.export_delta(target_audit, run_id, actor)
            return JSONResponse(_jsonable(res))
        if name == "score":
            if cfg.is_team():
                proj_uploads = (UPLOADS / proj).resolve()
                key = Path(d.get("key_path") or "")
                resolved_key = (proj_uploads / key).resolve() if not key.is_absolute() else key.resolve()
                if not resolved_key.is_file() or (
                    proj_uploads not in resolved_key.parents and resolved_key.parent != proj_uploads
                ):
                    raise ApiError("Answer key file not found", 404)
                key = resolved_key
            else:
                key = Path(d.get("key_path") or "")
                key = key if key.is_absolute() else PROJECT_ROOT / key
                if not key.is_file():
                    raise ApiError("Answer key file not found")
            kind = views.run_view(target_audit, run_id)["kind"]
            if kind == "delta":
                from harness.sift import delta as sift_delta

                return JSONResponse({
                    "rows": [
                        {
                            "label": "Expected changes",
                            **sift_delta.score(target_audit, run_id, key),
                        }
                    ]
                })
            rows_ = [
                ("Code checks only", ("code",), 1),
                ("AI reviewer only", ("ai",), 1),
                ("Code and AI together", ("code", "ai"), 1),
            ]
            n_pass = len(sift_check.passes_done(target_audit, run_id))
            if n_pass > 1:
                rows_.append((
                    f"Code and AI, AI findings seen in all {n_pass} passes",
                    ("code", "ai"),
                    n_pass,
                ))
            return JSONResponse({
                "rows": [
                    {
                        "label": lbl,
                        **sift_check.score(target_audit, run_id, key, srcs, min_passes=mp),
                    }
                    for lbl, srcs, mp in rows_
                ]
            })
        raise ApiError(f"Unknown action {name}", 404)

    # ---- new runs ----

    async def new_run(request: Request):
        if cfg.is_team():
            assert cfg.team is not None
            access = getattr(request.state, "access", None) or resolve_request_access(request)
            proj = request.query_params.get("project")
            if not proj and len(access.roles) == 1:
                proj = next(iter(access.roles.keys()))
            if proj:
                request.state.project = proj
                if proj not in cfg.team.projects:
                    raise ApiError(f"Unknown project '{proj}'.", 404)
                if proj not in access.roles and not access.admin:
                    raise ApiError(f"You do not have access to project '{proj}'.", 403)
                v = can(access, proj, "run")
                if not v.ok:
                    raise ApiError(v.reason, 403)
            elif not access.admin and not any(can(access, p, "run").ok for p in access.roles):
                raise ApiError("You do not have permission to start runs.", 403)

            max_bytes = cfg.team.max_upload_mb * 1024 * 1024
            # 1. Content-Length header check
            cl = request.headers.get("content-length")
            if cl:
                try:
                    if int(cl) > max_bytes:
                        raise ApiError(f"File is over {cfg.team.max_upload_mb} MB.", 413)
                except ValueError:
                    pass
            # 2. Running stream receive check
            total_received = 0
            orig_receive = request._receive

            async def limited_receive():
                nonlocal total_received
                msg = await orig_receive()
                if msg["type"] == "http.request":
                    total_received += len(msg.get("body", b""))
                    if total_received > max_bytes:
                        raise ApiError(f"File is over {cfg.team.max_upload_mb} MB.", 413)
                return msg

            request._receive = limited_receive
            form = await request.form(max_part_size=max_bytes)
        else:
            form = await request.form()

        kind = request.path_params["kind"]
        upload_id = uuid.uuid4().hex[:8]
        if cfg.is_team():
            assert cfg.team is not None
            proj = proj or form.get("project")
            if not proj and access.roles:
                proj = next(iter(access.roles.keys()))
            if not proj or proj not in cfg.team.projects:
                raise ApiError(f"Unknown project '{proj}'.", 404)
            if proj not in access.roles and not access.admin:
                raise ApiError(f"You do not have access to project '{proj}'.", 403)
            v = can(access, proj, "run")
            if not v.ok:
                raise ApiError(v.reason, 403)
            base_upload_dir = UPLOADS.resolve()
            upload_dir = (base_upload_dir / proj / upload_id).resolve()
            if base_upload_dir not in upload_dir.parents and upload_dir != base_upload_dir:
                raise ApiError(f"Unknown project '{proj}'.", 404)
            target_store = audit.scoped(proj, access.principal)
            principal_id = access.principal.id
        else:
            who(request, {"reviewer": form.get("reviewer")})  # a named person starts every run
            proj = None
            upload_dir = (UPLOADS / "personal" / upload_id).resolve()
            target_store = audit
            principal_id = None

        upload_dir.mkdir(parents=True, exist_ok=True)

        async def save(field: str) -> Path | None:
            up = form.get(field)
            if not up or not getattr(up, "filename", ""):
                return None
            dest = upload_dir / Path(up.filename).name

            max_bytes = (
                cfg.team.max_upload_mb * 1024 * 1024
                if cfg.is_team() and cfg.team
                else None
            )
            total_bytes = 0
            chunk_size = 64 * 1024
            with dest.open("wb") as f_out:
                while True:
                    res = up.read(chunk_size)
                    chunk = await res if asyncio.iscoroutine(res) else res
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes is not None and total_bytes > max_bytes:
                        f_out.close()
                        dest.unlink(missing_ok=True)
                        raise ApiError(f"File is over {cfg.team.max_upload_mb} MB.", 413)
                    f_out.write(chunk)
            return dest

        if kind == "sift":
            path = await save("file")
            if not path:
                raise ApiError("Choose a specification file.")
            return job_response(
                jobs.start(
                    None,
                    "Reading the document and mapping sections",
                    lambda: pipeline.start(cfg, target_store, path),
                    project=proj,
                    principal_id=principal_id,
                )
            )
        if kind == "check":
            path = await save("file")
            if not path:
                raise ApiError("Choose a requirement set.")
            style = "ears" if form.get("ears") == "true" else None
            source = await save("source")
            rules = form.get("rules") or None
            if not rules and cfg.is_team() and proj:
                assert cfg.team is not None
                ps = cfg.team.projects.get(proj)
                if ps and ps.rule_profile:
                    rules = ps.rule_profile
            try:
                rep = sift_check.start(
                    cfg, target_store, path, style=style, rules=rules, source=source
                )
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
                run_id = start_tests(target_store, [tests], dbc, reqs)
            except (ValueError, OSError) as e:
                raise ApiError(str(e)) from e
            return JSONResponse({"run_id": run_id})
        if kind == "delta":
            from harness.sift import delta as sift_delta

            new = await save("new")
            if form.get("mode") == "spec":
                if not (new and form.get("base")):
                    raise ApiError("Choose the approved Sift run and the new revision.")
                rep = sift_delta.spec_delta(cfg, target_store, form["base"], new)
            else:
                old = await save("old")
                if not (old and new):
                    raise ApiError("Choose both requirement sets.")
                rep = sift_delta.set_delta(cfg, target_store, old, new)
            return JSONResponse(_jsonable(rep))
        if kind == "forge":
            from harness.anvil import pipeline as forge

            dbc = await save("dbc") or PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"
            base = form.get("base")
            if not base:
                raise ApiError("Choose an approved Sift run.")
            return job_response(
                jobs.start(
                    None,
                    "Proposing a test template for each approved requirement",
                    lambda: forge.start(cfg, target_store, base, dbc),
                    project=proj,
                    principal_id=principal_id,
                )
            )
        raise ApiError(f"Unknown run kind {kind}", 404)

    async def team_settings(request: Request) -> JSONResponse:
        if not cfg.is_team():
            raise ApiError("Not in team mode", 404)
        access = getattr(request.state, "access", None) or resolve_request_access(request)
        if not access.admin:
            raise ApiError("Admin actions require admin role.", 403)
        assert cfg.team is not None
        data = cfg.team.model_dump()
        data["session_secret"] = "set" if cfg.team.session_secret else "missing"
        data["oidc"]["client_secret"] = "set" if cfg.team.oidc.client_secret else "missing"
        if "service_accounts" in data:
            for sa in data["service_accounts"].values():
                if "token_sha256" in sa:
                    sa["token_sha256"] = "set" if sa["token_sha256"] else "missing"
        data["rule_profiles"] = list_profiles()
        return JSONResponse(data)

    async def get_tokens(request: Request) -> JSONResponse:
        if not cfg.is_team():
            raise ApiError("Not in team mode", 404)
        access = getattr(request.state, "access", None) or resolve_request_access(request)
        if access.principal.kind != "person":
            raise ApiError("Tokens can only be managed from a browser session.", 403)
        with audit.backend.connect() as con:
            rows = con.execute(
                "SELECT token_id, label, created_at, expires_at FROM tokens WHERE owner_id=? ORDER BY created_at DESC",
                (access.principal.id,),
            )
            t_rev = con.execute("SELECT detail_json FROM events WHERE action = 'token_revoked'")
            revoked_ids = set()
            for r in t_rev:
                if r["detail_json"]:
                    dtl = json.loads(r["detail_json"])
                    if "token_id" in dtl:
                        revoked_ids.add(dtl["token_id"])
        res = [
            {
                "token_id": r["token_id"],
                "label": r["label"],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "revoked": r["token_id"] in revoked_ids,
            }
            for r in rows
        ]
        return JSONResponse(res)

    async def post_token(request: Request) -> JSONResponse:
        if not cfg.is_team():
            raise ApiError("Not in team mode", 404)
        access = getattr(request.state, "access", None) or resolve_request_access(request)
        if access.principal.kind != "person":
            raise ApiError("Tokens can only be managed from a browser session.", 403)
        d = await body(request)
        label = (d.get("label") or "Personal access token").strip()
        assert cfg.team is not None
        try:
            days_req = int(d.get("days") or cfg.team.token_days)
        except (ValueError, TypeError):
            days_req = cfg.team.token_days
        days = min(max(1, days_req), cfg.team.token_days)
        from harness.team.tokens import create_token

        token_id, secret = create_token(
            audit, access.principal, label, days=days, max_days=cfg.team.token_days
        )
        return JSONResponse({"token_id": token_id, "secret": secret}, status_code=201)

    async def post_revoke_token(request: Request) -> JSONResponse:
        if not cfg.is_team():
            raise ApiError("Not in team mode", 404)
        access = getattr(request.state, "access", None) or resolve_request_access(request)
        if access.principal.kind != "person":
            raise ApiError("Tokens can only be managed from a browser session.", 403)
        token_id = request.path_params["token_id"]
        with audit.backend.connect() as con:
            rows = con.execute("SELECT owner_id FROM tokens WHERE token_id=?", (token_id,))
        if not rows:
            raise ApiError("No such token", 404)
        if rows[0]["owner_id"] != access.principal.id and not access.admin:
            raise ApiError("Not authorized to revoke this token", 403)
        from harness.team.tokens import revoke_token

        revoke_token(audit, token_id, by=access.principal)
        return JSONResponse({"ok": True})

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
        Route("/api/health", health),
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
    if cfg.is_team():
        routes.extend([
            Route("/api/team-settings", team_settings),
            Route("/api/tokens", get_tokens, methods=["GET"]),
            Route("/api/tokens", post_token, methods=["POST"]),
            Route("/api/tokens/{token_id}/revoke", post_revoke_token, methods=["POST"]),
            Route("/auth/login", auth_login),
            Route("/auth/fake-sign-in", auth_login),
            Route("/auth/callback", auth_callback),
            Route("/auth/logout", auth_logout, methods=["GET", "POST"]),
        ])
    if (WEB_DIST / "assets").is_dir():
        routes.append(Mount("/assets", StaticFiles(directory=WEB_DIST / "assets")))
    routes.append(Route("/{path:path}", index))

    middleware = []
    if cfg.is_team():
        assert cfg.team is not None
        insecure_allowed = getattr(cfg.team, "allow_insecure_http", False) or getattr(
            cfg.team, "trial", False
        )
        https_only = not insecure_allowed
        middleware.append(Middleware(BaseHTTPMiddleware, dispatch=access_log_middleware))
        middleware.append(
            Middleware(
                SessionMiddleware,
                secret_key=cfg.team.session_secret,
                max_age=cfg.team.session_hours * 3600,
                https_only=https_only,
                same_site="lax",
            )
        )
        middleware.append(Middleware(BaseHTTPMiddleware, dispatch=auth_gate))

    handlers = {
        ApiError: on_error,
        ValueError: on_error,
        KeyError: on_error,
        StructuredOutputFailure: on_error,
        Exception: on_error,
    }
    app = Starlette(routes=routes, middleware=middleware, exception_handlers=handlers)
    app.state.jobs = jobs
    app.state.idp = idp
    return app
