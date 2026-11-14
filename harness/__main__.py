"""Command line entry point.

    python -m harness profiles                 list model profiles and whether each is reachable
    python -m harness smoke                    run the P0 smoke test with the configured roles
    python -m harness smoke --generator local-qwen3-14b --reviewer claude-opus
    python -m harness smoke --no-review        skip the AI reviewer
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import PROJECT_ROOT, load_config
from harness.models.runner import StructuredOutputFailure


def _screen_hint() -> str:
    """How to open the review screen: the Windows launcher in a source folder, else zyn serve."""
    if os.name == "nt" and (PROJECT_ROOT / "review.ps1").is_file():
        return ".\\review.ps1"
    return "zyn serve"


def _ollama_models(host: str) -> list[str] | None:
    try:
        import ollama

        listing = ollama.Client(host=host, timeout=3).list()
        return [m.model for m in listing.models]
    except Exception:  # noqa: BLE001 - any failure here just means "not reachable"
        return None


def cmd_profiles(cfg) -> int:
    from harness.models.readiness import profile_readiness

    print(f"{PROTOTYPE_LABEL}\n")
    print("Roles: " + ", ".join(f"{r} -> {p}" for r, p in cfg.roles.items()) + "\n")
    for name, p in cfg.profiles.items():
        _, state = profile_readiness(cfg, p)
        print(f"  {name:22} {p.provider:9} {p.model:20} {state}")
    return 0


def cmd_smoke(cfg, args) -> int:
    from harness.smoke import run_smoke

    audit = AuditStore(cfg.resolved_db_path())
    reviewer = None if args.no_review else args.reviewer
    try:
        summary = run_smoke(cfg, audit, generator=args.generator, reviewer=reviewer)
    except StructuredOutputFailure as e:
        print(f"FAILED: {e}\nDetails are in the audit log ({cfg.resolved_db_path()}).")
        return 1
    print(json.dumps(summary, indent=2))
    print("\nNext: open the review screen and approve or reject each item:")
    print(f"  {_screen_hint()}")
    return 0


def cmd_sift(cfg, args) -> int:
    from harness.sift import pipeline
    from harness.sift.export import export

    audit = AuditStore(cfg.resolved_db_path())
    try:
        if args.stage == "start":
            rep = pipeline.start(cfg, audit, args.target, generator=args.generator)
        elif args.stage == "extract":
            rep = pipeline.extract(cfg, audit, args.target, generator=args.generator,
                                   reviewer=None if args.no_review else args.reviewer)
        elif args.stage == "clarify":
            rep = pipeline.clarify(cfg, audit, args.target, model=args.generator)
        else:
            if not args.reviewer_name:
                print("Export needs --as <your name> for the audit log.")
                return 1
            print(json.dumps(export(audit, args.target, args.reviewer_name), indent=2))
            return 0
    except (StructuredOutputFailure, ValueError) as e:
        print(f"FAILED: {e}")
        return 1
    print(json.dumps(rep.as_dict(), indent=2))
    print(f"\nNext: review in the browser:  {_screen_hint()}")
    return 0 if not rep.failed else 1


def cmd_check(cfg, args) -> int:
    from harness.sift import check

    audit = AuditStore(cfg.resolved_db_path())
    try:
        if args.stage == "start":
            rep = check.start(cfg, audit, args.target, style=args.style, rules=args.rules,
                              source=args.source)
        elif args.stage == "ai":
            rep = check.ai_review(cfg, audit, args.target, reviewer=args.reviewer)
        elif args.stage == "stability":
            rep = check.stability_check(cfg, audit, args.target, args.passes,
                                        reviewer=args.reviewer)
        elif args.stage == "score":
            print(json.dumps(check.score(audit, args.target, args.key,
                                         min_passes=args.min_passes), indent=2))
            return 0
        else:
            if not args.reviewer_name:
                print("Export needs --as <your name> for the audit log.")
                return 1
            print(json.dumps(check.export_findings(audit, args.target, args.reviewer_name),
                             indent=2))
            return 0
    except (StructuredOutputFailure, ValueError, FileNotFoundError) as e:
        print(f"FAILED: {e}")
        return 1
    print(json.dumps(rep.as_dict(), indent=2))
    print(f"\nNext: review the findings in the browser:  {_screen_hint()}")
    return 0 if not rep.failed else 1


def cmd_delta(cfg, args) -> int:
    from harness.sift import delta

    audit = AuditStore(cfg.resolved_db_path())
    try:
        if args.stage == "spec":
            rep = delta.spec_delta(cfg, audit, args.a, args.b)
        elif args.stage == "set":
            rep = delta.set_delta(cfg, audit, args.a, args.b)
        elif args.stage == "score":
            print(json.dumps(delta.score(audit, args.a, args.key), indent=2))
            return 0
        else:
            if not args.reviewer_name:
                print("Export needs --as <your name> for the audit log.")
                return 1
            print(json.dumps(delta.export_delta(audit, args.a, args.reviewer_name), indent=2))
            return 0
    except ValueError as e:
        print(f"FAILED: {e}")
        return 1
    print(json.dumps(rep.as_dict(), indent=2))
    return 0


def cmd_forge(cfg, args) -> int:
    from harness.anvil import pipeline as forge

    audit = AuditStore(cfg.resolved_db_path())
    try:
        if args.stage == "repropose":
            rep = forge.repropose(cfg, audit, args.target, generator=args.generator)
            print(json.dumps(rep.as_dict(), indent=2))
            return 0 if not rep.failed else 1
        if args.stage in ("start", "resume"):
            rep = (forge.start(cfg, audit, args.target, args.dbc, generator=args.generator)
                   if args.stage == "start" else
                   forge.resume(cfg, audit, args.target, generator=args.generator))
            print(json.dumps(rep.as_dict(), indent=2))
            return 0 if not rep.failed else 1
        if args.stage == "formal":
            from harness.anvil.formal import run_check
            print(json.dumps(run_check(audit, args.target), indent=2))
            return 0
        if args.stage == "score":
            from harness.anvil.score import kill_score
            print(json.dumps(kill_score(audit, args.target), indent=2))
            return 0
        if not args.reviewer_name:
            print(f"{args.stage} needs --as <your name> for the audit log.")
            return 1
        fn = forge.generate if args.stage == "generate" else forge.export
        print(json.dumps(fn(audit, args.target, args.reviewer_name), indent=2))
        return 0
    except (StructuredOutputFailure, ValueError) as e:
        print(f"FAILED: {e}")
        return 1


def cmd_rules(cfg, args) -> int:
    from harness.sift import custom, rules

    audit = AuditStore(cfg.resolved_db_path())
    if args.stage == "list":
        print(json.dumps({"profiles": rules.list_profiles(), "checks": rules.CODE_CHECKS},
                         indent=2))
        return 0
    if args.stage in ("learn", "learn-accept"):
        from harness import learn
        props = learn.proposals(audit, args.profile)
        if args.stage == "learn":
            print(json.dumps(props, indent=2) if props else
                  "No proposals: not enough repeated decisions yet.")
            return 0
        pick = next((p for p in props if p["id"] == args.text), None)
        if pick is None:
            print(f"No current proposal {args.text}. Run: rules learn")
            return 1
        try:
            print(f"Applied to {learn.accept(audit, pick, args.reviewer_name or '', cfg)}")
        except ValueError as e:
            print(f"FAILED: {e}")
            return 1
        return 0
    if args.stage == "calibration":
        from harness.calibration import table
        print(json.dumps(table(audit), indent=2))
        return 0
    if not args.text:
        print(f"{args.stage} needs the rule text or check name.")
        return 1
    try:
        if args.stage == "draft":
            from harness.sift.importer import load_requirement_set
            path = args.reqset or str(PROJECT_ROOT / "data" / "synthetic" / "icx100_reqset.csv")
            reqs = [{"ext_id": r.ext_id, "text": r.text}
                    for r in load_requirement_set(path).requirements]
            print(json.dumps(custom.draft(cfg, audit, args.text, reqs), indent=2))
        else:
            print(f"Added to {custom.accept(args.text, args.into, args.reviewer_name or '')}")
    except (StructuredOutputFailure, ValueError, FileNotFoundError) as e:
        print(f"FAILED: {e}")
        return 1
    return 0


def cmd_evidence(cfg, args) -> int:
    from harness import evidence

    if args.stage == "verify":
        data = json.loads(Path(args.target).read_text(encoding="utf-8"))
        ok, bad = evidence.verify_chain(data)
        print("Audit chain intact." if ok else f"Audit chain BROKEN at event index {bad}.")
        return 0 if ok else 1
    if not args.reviewer_name:
        print("report needs --as <your name> for the audit log.")
        return 1
    res = evidence.export_evidence(AuditStore(cfg.resolved_db_path()), args.target,
                                   args.reviewer_name, cfg)
    print(json.dumps(res, indent=2))
    return 0


def cmd_serve(cfg, args) -> int:
    import threading
    import webbrowser

    import uvicorn

    from harness.api.server import create_app

    fake_sign_in = None
    if getattr(args, "fake_sign_in", None):
        if os.environ.get("ZYN_DEV") != "1":
            print("serve --fake-sign-in requires ZYN_DEV=1 in environment.", file=sys.stderr)
            return 2
        is_team = getattr(args, "team", False) or cfg.is_team()
        if not is_team:
            print("serve --fake-sign-in requires --team mode.", file=sys.stderr)
            return 2
        parts = [p.strip() for p in args.fake_sign_in.split(",") if p.strip()]
        if not parts:
            print("serve --fake-sign-in requires NAME,GROUPS.", file=sys.stderr)
            return 2
        name = parts[0]
        groups = parts[1:]
        fake_sign_in = (name, groups)

    if getattr(args, "team", False) and not cfg.is_team():
        print("serve --team needs a team section in config.yaml.", file=sys.stderr)
        return 2

    host = getattr(args, "host", "127.0.0.1")
    is_team = getattr(args, "team", False) or cfg.is_team()
    if not is_team and host in ("0.0.0.0", "::"):
        print("Personal mode only listens on this machine.", file=sys.stderr)
        return 2

    url = f"http://{host}:{args.port}"
    print(f"{PROTOTYPE_LABEL} Review screen at {url}  (Ctrl+C to stop)")
    if not args.no_browser and host == "127.0.0.1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(cfg, fake_sign_in=fake_sign_in), host=host, port=args.port, log_level="warning")
    return 0


DEMO_SET = PROJECT_ROOT / "data" / "synthetic" / "icx100_reqset.csv"
DEMO_SOURCE = PROJECT_ROOT / "data" / "synthetic" / "icx100_srs.md"
DEMO_MARKER = PROJECT_ROOT / "runs" / "demo_run.txt"


def demo_run(cfg) -> tuple[str, bool]:
    """The sample requirement set checked against its specification by code alone: no
    model, no key. Reuses the earlier demo run if it is still in the audit log.
    Returns (run_id, created)."""
    from harness.sift import check

    audit = AuditStore(cfg.resolved_db_path())
    if DEMO_MARKER.is_file():
        rid = DEMO_MARKER.read_text(encoding="utf-8").strip()
        if any(r["run_id"] == rid for r in audit.list_runs()):
            return rid, False
    rep = check.start(cfg, audit, DEMO_SET, source=DEMO_SOURCE)
    DEMO_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DEMO_MARKER.write_text(rep.run_id, encoding="utf-8")
    return rep.run_id, True


def cmd_demo(cfg, args) -> int:
    if not DEMO_SET.is_file():
        print(f"Sample data not found in {DEMO_SET.parent}.")
        return 1
    run_id, created = demo_run(cfg)
    findings = len(AuditStore(cfg.resolved_db_path()).list_items(run_id, "finding"))
    word = "Checked" if created else "Already checked"
    print(f"{word} the sample requirement set against its specification, by code alone "
          f"(no model, no key): {findings} findings in run {run_id}.")
    print(f"Your Zyn folder: {PROJECT_ROOT}")
    return cmd_serve(cfg, args)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(prog="zyn", description=PROTOTYPE_LABEL)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profiles", help="list model profiles and readiness")
    s = sub.add_parser("smoke", help="run the P0 smoke test")
    s.add_argument("--generator", default="generator", help="role or profile name")
    s.add_argument("--reviewer", default="reviewer", help="role or profile name")
    s.add_argument("--no-review", action="store_true", help="skip the AI reviewer")
    f = sub.add_parser("sift", help="Sift stages: start <file> | extract <run> | "
                                         "clarify <run> | export <run> --as NAME")
    f.add_argument("stage", choices=["start", "extract", "clarify", "export"])
    f.add_argument("target", help="file path for start, run id for the other stages")
    f.add_argument("--generator", default="generator")
    f.add_argument("--reviewer", default="reviewer")
    f.add_argument("--no-review", action="store_true")
    f.add_argument("--as", dest="reviewer_name", help="your name, recorded on export")
    c = sub.add_parser("check", help="Sift Review of an existing requirement set: "
                                     "start <file> | ai <run> | export <run> --as NAME | "
                                     "score <run> --key FILE")
    c.add_argument("stage", choices=["start", "ai", "stability", "export", "score"])
    c.add_argument("--passes", type=int, default=3, help="stability: AI passes in total")
    c.add_argument("--style", choices=["ears"], help="start: also check EARS sentence patterns")
    c.add_argument("--rules", help="start: rule profile from rules/ (default: default)")
    c.add_argument("--source", help="start: the specification the set was drawn from, to "
                                    "check each requirement against it (checker mode)")
    tc = sub.add_parser("testcheck", help="Anvil Review: tests from any tool against a DBC and a "
                                          "requirement set (checker mode)")
    tc.add_argument("tests", nargs="+", help="test files: .py, .can, .robot, .txt, ...")
    tc.add_argument("--dbc", default=str(PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"))
    tc.add_argument("--reqs", help="requirement set (ReqIF, Excel, CSV) the tests refer to")
    c.add_argument("--min-passes", type=int, default=1,
                   help="score: count AI findings only if seen in this many passes")
    c.add_argument("target", help="ReqIF/XLSX/CSV file for start, run id for the others")
    c.add_argument("--reviewer", default="reviewer")
    c.add_argument("--as", dest="reviewer_name", help="your name, recorded on export")
    c.add_argument("--key", default=str(PROJECT_ROOT / "data" / "synthetic"
                                        / "icx100_answer_key.json"))
    d = sub.add_parser("delta", help="Sift Delta: spec <sift run> <new spec> | set <old file> "
                                     "<new file> | export <run> --as NAME | score <run> --key")
    d.add_argument("stage", choices=["spec", "set", "export", "score"])
    d.add_argument("a", help="base Sift run (spec), old set file (set), or delta run id")
    d.add_argument("b", nargs="?", help="new spec or new set file")
    d.add_argument("--as", dest="reviewer_name")
    d.add_argument("--key", default=str(PROJECT_ROOT / "data" / "synthetic"
                                        / "icx100_rev2_changes.json"))
    b = sub.add_parser("bench", help="run the same tasks on several models and compare")
    b.add_argument("--profiles", default="claude-opus,claude-sonnet,claude-haiku,"
                   "local-qwen3-14b", help="comma-separated profile names")
    b.add_argument("--tasks", default="map,check", help="map, check or both")
    b.add_argument("--repeat", type=int, default=2, help="runs per model and task")
    g = sub.add_parser("anvil", aliases=["forge"],
                       help="Anvil (formerly Forge): start <sift run> [--dbc FILE] | "
                            "resume <run> | generate <run> --as NAME | export <run> --as NAME "
                            "| score <run>")
    g.add_argument("stage", choices=["start", "resume", "repropose", "generate", "export",
                                     "score", "formal"])
    g.add_argument("target", help="approved Sift run (start) or Anvil run id")
    g.add_argument("--dbc", default=str(PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"))
    g.add_argument("--generator", default="generator")
    g.add_argument("--as", dest="reviewer_name")
    m = sub.add_parser("metrics", help="effort, cost and agreement figures for one run")
    m.add_argument("run_id")
    w = sub.add_parser("serve", help="open the review screen in your browser")
    w.add_argument("--host", default="127.0.0.1", help="host to listen on (0.0.0.0 only allowed with --team)")
    w.add_argument("--team", action="store_true", help="run in team mode")
    w.add_argument("--fake-sign-in", metavar="NAME,GROUPS", help="dev only: pretend sign-in with NAME,GROUPS (requires ZYN_DEV=1)")
    w.add_argument("--port", type=int, default=8600)
    w.add_argument("--no-browser", action="store_true")
    dm = sub.add_parser("demo", help="check the sample data by code alone (no key) and open "
                                     "the review screen")
    dm.add_argument("--port", type=int, default=8600)
    dm.add_argument("--no-browser", action="store_true")
    dm.add_argument("--no-serve", action="store_true", help="check only, do not open the screen")
    sub.add_parser("where", help="show the Zyn folder: config, rules, audit log and exports")
    ru = sub.add_parser("rules", help="rule profiles and custom checks: list | draft \"<rule>\" "
                                      "[--set FILE] | accept NAME --into PROFILE --as NAME")
    ru.add_argument("stage", choices=["list", "draft", "accept", "calibration", "learn",
                                      "learn-accept"])
    ru.add_argument("text", nargs="?", help="draft: the rule in plain words; accept: check name")
    ru.add_argument("--set", dest="reqset", help="draft: requirement set to try the check on")
    ru.add_argument("--into", default="default", help="accept: rule profile to add it to")
    ru.add_argument("--as", dest="reviewer_name", help="accept: your name")
    ru.add_argument("--profile", default="default", help="learn: rule profile to improve")
    pk = sub.add_parser("pack", help="benchmark pack: manifest | run --profiles A,B | export")
    pk.add_argument("stage", choices=["manifest", "run", "export"])
    pk.add_argument("--profiles", default="claude-sonnet,claude-haiku")
    pk.add_argument("--tasks", help="comma list (default: every task whose data is present)")
    pk.add_argument("--repeat", type=int, default=3)
    pk.add_argument("--knowledge", help="run: add this knowledge file to every call (A/B)")
    sub.add_parser("mcp", help="serve Zyn's checks as MCP tools over stdio (for Claude Code "
                               "and other MCP clients)")
    ev = sub.add_parser("evidence", help="evidence report: report <run> --as NAME | verify "
                                         "<audit_chain.json>")
    ev.add_argument("stage", choices=["report", "verify"])
    ev.add_argument("target", help="run id (report) or audit_chain.json (verify)")
    ev.add_argument("--as", dest="reviewer_name", help="your name, recorded on the report")
    up = sub.add_parser("upgrade", help="apply database migrations and set up permissions")
    up.add_argument("--admin-url", default=os.environ.get("ZYN_DATABASE_ADMIN_URL", ""),
                    help="PostgreSQL URL with admin rights")
    up.add_argument("--app-user", default="", help="PostgreSQL user name that Zyn runs as")
    up.add_argument("--app-password", default="",
                    help="password if app user role needs to be created (prefer ZYN_DATABASE_APP_PASSWORD env var)")
    imp = sub.add_parser(
        "import-log", help="import a personal SQLite audit log into a team project"
    )
    imp.add_argument("file", help="path to SQLite database file")
    imp.add_argument("--project", required=True, help="team project to assign imported runs to")
    imp.add_argument(
        "--admin-url",
        default=os.environ.get("ZYN_DATABASE_ADMIN_URL", ""),
        help="PostgreSQL URL with admin rights",
    )
    rev = sub.add_parser("revoke-person", help="revoke a person's sessions")
    rev.add_argument("person_id", help="principal id to revoke, e.g. oidc:issuer#sub")
    rev.add_argument("--as", dest="reviewer", required=True, help="admin name for audit log")
    rem = sub.add_parser("remote", help="interact with a remote Zyn team server")
    rem.add_argument(
        "--server",
        default=os.environ.get("ZYN_SERVER", "http://127.0.0.1:8600"),
        help="server URL",
    )
    rem.add_argument("--project", help="project identifier")
    rem.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="exit with 1 if check produces open findings",
    )
    rem_sub = rem.add_subparsers(dest="remote_cmd", required=True)
    rem_sub.add_parser("runs", help="list runs on the server")
    rc = rem_sub.add_parser("check", help="upload and check requirements")
    rc.add_argument("file", help="requirement file (CSV, XLSX, ReqIF)")
    rc.add_argument("--source", help="source specification document")
    rc.add_argument("--rules", help="rule profile")
    rc.add_argument("--ears", action="store_true", help="check EARS patterns")
    rtc = rem_sub.add_parser("testcheck", help="upload and check tests against DBC")
    rtc.add_argument("tests", nargs="+", help="test files")
    rtc.add_argument("--dbc", required=True, help="DBC signal specification file")
    rtc.add_argument("--reqs", help="requirement set file")
    rd = rem_sub.add_parser("delta", help="compare two requirement sets")
    rd.add_argument("old", help="old requirement set file")
    rd.add_argument("new", help="new requirement set file")
    rf = rem_sub.add_parser("findings", help="get findings for a run as JSON")
    rf.add_argument("run_id", help="run identifier")
    re = rem_sub.add_parser("export", help="export run results to file")
    re.add_argument("run_id", help="run identifier")
    re.add_argument("--as-file", required=True, help="destination file path")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    team_allowed = {"serve", "upgrade", "import-log", "revoke-person", "where", "remote"}
    cmd = args.cmd or "smoke"
    if cfg.is_team() and cmd not in team_allowed:
        print("This Zyn folder is a team server. Use zyn remote, or the review screen.")
        return 2

    if args.cmd == "revoke-person":
        db_target = (
            cfg.team.database_url
            if cfg.is_team() and cfg.team and cfg.team.database_url
            else cfg.resolved_db_path()
        )
        store = AuditStore(db_target)
        store.log_event(
            actor=args.reviewer,
            action="person_revoked",
            object_id=args.person_id,
            actor_id=None,
            detail={"person_id": args.person_id},
        )
        print(f"Revoked sessions for {args.person_id}")
        return 0
    if args.cmd == "upgrade":
        from harness.audit.migrations import upgrade

        admin_url = args.admin_url or os.environ.get("ZYN_DATABASE_ADMIN_URL", "")
        if not admin_url:
            print(
                "upgrade needs --admin-url or ZYN_DATABASE_ADMIN_URL in environment",
                file=sys.stderr,
            )
            return 2
        app_password = os.environ.get("ZYN_DATABASE_APP_PASSWORD", "") or getattr(
            args, "app_password", ""
        )
        applied = upgrade(admin_url, args.app_user, app_password=app_password)
        if applied:
            print(f"Applied migrations: {applied}")
        else:
            print("Database schema is already up to date.")
        return 0
    if args.cmd == "import-log":
        if cfg.is_team() and not args.admin_url:
            print("import-log requires --admin-url in team mode", file=sys.stderr)
            return 2
        if cfg.is_team() and cfg.team and args.project not in cfg.team.projects:
            known = ", ".join(sorted(cfg.team.projects))
            print(
                f"Unknown project '{args.project}'. Configured projects: {known}",
                file=sys.stderr,
            )
            return 2
        from harness.team.importlog import import_log

        target_db = args.admin_url or (
            cfg.team.database_url
            if cfg.is_team() and cfg.team and cfg.team.database_url
            else cfg.resolved_db_path()
        )
        store = AuditStore(target_db)
        res = import_log(Path(args.file), store, args.project, team=cfg.team)
        print(json.dumps(res, indent=2))
        return 0
    if args.cmd == "remote":
        from harness.team.remote import cmd_remote

        return cmd_remote(args)
    if args.cmd == "profiles":
        return cmd_profiles(cfg)
    if args.cmd == "sift":
        return cmd_sift(cfg, args)
    if args.cmd == "check":
        return cmd_check(cfg, args)
    if args.cmd in ("anvil", "forge"):
        return cmd_forge(cfg, args)
    if args.cmd == "delta":
        return cmd_delta(cfg, args)
    if args.cmd == "bench":
        from harness.bench import benchmark
        res = benchmark(cfg, AuditStore(cfg.resolved_db_path()), args.profiles.split(","),
                        tuple(args.tasks.split(",")), args.repeat)
        print(Path(res["files"]["md"]).read_text(encoding="utf-8"))
        return 0
    if args.cmd == "serve":
        return cmd_serve(cfg, args)
    if args.cmd == "demo":
        if args.no_serve:
            run_id, _ = demo_run(cfg)
            print(json.dumps({"run_id": run_id, "findings": len(AuditStore(
                cfg.resolved_db_path()).list_items(run_id, "finding"))}, indent=2))
            return 0
        return cmd_demo(cfg, args)
    if args.cmd == "where":
        print(f"Zyn folder:  {PROJECT_ROOT}")
        print(f"Config:      {args.config}")
        print(f"Audit log:   {cfg.resolved_db_path()}")
        print(f"API key:     {PROJECT_ROOT / '.env'} (copy .env.example; only the AI steps "
              "need it)")
        return 0
    if args.cmd == "evidence":
        return cmd_evidence(cfg, args)
    if args.cmd == "rules":
        return cmd_rules(cfg, args)
    if args.cmd == "pack":
        from harness import pack
        if args.stage == "manifest":
            print(json.dumps(pack.manifest(), indent=2))
        elif args.stage == "export":
            print(json.dumps(pack.export(), indent=2))
        else:
            res = pack.run_pack(args.profiles.split(","),
                                args.tasks.split(",") if args.tasks else None, args.repeat,
                                knowledge=Path(args.knowledge) if args.knowledge else None)
            print(Path(res["files"]["md"]).read_text(encoding="utf-8"))
        return 0
    if args.cmd == "mcp":
        from harness.mcp_server import serve
        for stream in (sys.stdin, sys.stdout):
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        serve()
        return 0
    if args.cmd == "testcheck":
        from harness.outside import start_tests
        audit = AuditStore(cfg.resolved_db_path())
        try:
            run_id = start_tests(audit, [Path(t) for t in args.tests], Path(args.dbc),
                                 Path(args.reqs) if args.reqs else None)
        except ValueError as e:
            print(f"Not checked: {e}")
            return 1
        meta = audit.get_item(f"SET-{run_id}")["payload"]
        print(json.dumps({"run_id": run_id, "tests": meta["count"],
                          "findings": len(audit.list_items(run_id, "finding")),
                          "coverage": meta["coverage"]}, indent=2))
        print(f"\nNext: review the findings in the browser:  {_screen_hint()}")
        return 0
    if args.cmd == "metrics":
        from harness.metrics import run_metrics
        print(json.dumps(run_metrics(AuditStore(cfg.resolved_db_path()), args.run_id, cfg),
                         indent=2, default=str))
        return 0
    return cmd_smoke(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
