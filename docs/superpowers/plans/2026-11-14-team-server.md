# Team Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A team at a vehicle maker runs Zyn on its own server or cloud account, signs in with company accounts, works inside projects with per-project roles and a four-eyes rule, on a shared PostgreSQL audit log, while the single-PC install keeps working unchanged.

**Architecture:** Personal mode (today) and team mode share one codebase. Team mode is switched on by a `team:` section in `config.yaml`. Identity enters through one place (`who()` in `harness/api/server.py` becomes a `Principal` resolver); rules live in a new `harness/team/` package and are computed in `views.py` and enforced in `server.py`. The audit store gets a pluggable backend (SQLite or PostgreSQL) and a scoped view that stamps and filters by project and person.

**Tech Stack:** Python 3.11, Starlette, uvicorn, SQLite, PostgreSQL 16 via `psycopg[binary]>=3.2`, OpenID Connect via `authlib>=1.3`, sessions via Starlette `SessionMiddleware` (`itsdangerous`), React 18 + TypeScript (existing `web/`), Docker.

**Spec:** `docs/superpowers/specs/2026-11-14-enterprise-ready-design.md` (project 1). Read it before starting.

## Global Constraints

- Personal mode must behave exactly as today: typed reviewer name, SQLite file, `127.0.0.1` only. All 213 existing tests keep passing after every task.
- Rules live in Python: computed in `harness/api/views.py`, enforced again in `harness/api/server.py`. The screen only shows them.
- Append-only holds on both back ends: no UPDATE or DELETE on `runs`, `items`, `events`, `tokens`.
- Nothing is sent to Zyn's makers: no telemetry, no update checks, no licence calls.
- New team dependencies go in a `team` extra in `pyproject.toml`, never in core dependencies (`tests/test_install.py` guards core).
- UI follows `docs/design-system.md`: components from `web/src/components/`, tokens only in `web/src/styles/tokens.css`, icons only from the Zyn identity set, every state covered, sentence case, no em dashes.
- Public or synthetic data only in tests and fixtures.
- Before calling any task done: `.\.venv\Scripts\python -m pytest -q`, `.\.venv\Scripts\ruff check harness tests`; for tasks touching `web/`: `npx tsc -b` and `npx vite build` in `web/`.
- Work on a branch `team-server` in a worktree (superpowers:using-git-worktrees); the main checkout has unrelated uncommitted website work.
- Copy for the four-eyes refusal, verbatim: "You edited this; someone else must decide on it." and "You started this run; someone else must decide on its findings."
- Copy for a person recorded before sign-in, verbatim: "name typed, not signed in".

## Review Focus

1. **A session or token for a person who has since lost a group** must lose access on their next request, not keep it until the session ends. Test in Task 7.
2. **A run or item ID from another project typed into the URL or a POST body** must get 404, never the data. Test in Task 8.
3. **Bulk approval** (`/api/bulk`) must apply the four-eyes rule per item and skip, not fail, the ones the person may not decide. Test in Task 8.
4. **A background job (AI review) started by one person** must log its events under that person and that project, even though it runs on another thread after the request ends. Test in Task 2.
5. **Replay of a stored AI answer across projects** must never happen, even with an identical prompt and input. Test in Task 2.

---

### Task 1: Store back end split and new identity columns (SQLite only)

**Files:**
- Create: `harness/audit/backend.py`
- Modify: `harness/audit/store.py`, `harness/evidence.py` (`_canon`)
- Test: `tests/test_store_backend.py`

**Interfaces:**
- Produces: `class Backend(Protocol)` with `connect() -> ContextManager[Conn]`, `schema() -> list[str]`, `name: str`; `class SqliteBackend(path: Path)`; `Conn.execute(sql: str, args: Sequence = ()) -> list[dict]`, `Conn.insert(sql: str, args) -> int` (returns new row id), `Conn.claim_lock() -> None` (SQLite: `BEGIN IMMEDIATE`). Store SQL keeps `?` placeholders.
- Produces: `AuditStore(target: Path | str | Backend)`; a `Path`/`str` that is not a `postgresql://` URL means SQLite, as today.
- Produces: nullable columns `runs.project`, `runs.started_by_id`, `items.created_by_id`, `events.actor_id`. Existing SQLite files get them by `ALTER TABLE ... ADD COLUMN` on open (allowed by the append-only triggers).

- [ ] **Step 1: Write the failing tests**

```python
def test_old_sqlite_file_gains_columns_and_keeps_rows(tmp_path):
    # build a file with the pre-team SCHEMA (copied into the test), insert one run,
    # open it with AuditStore, assert the run is still there and
    # {"project","started_by_id"} <= run keys, and events have "actor_id"

def test_append_only_still_enforced(tmp_path):
    # UPDATE and DELETE on runs, items, events raise sqlite3.IntegrityError / DatabaseError

def test_evidence_chain_of_pre_team_events_is_unchanged(tmp_path, cfg):
    # audit_chain() head for a run equals the head computed with an event dict
    # that has no "actor_id" key at all (simulating an export made before this change)
```

- [ ] **Step 2: Run them, expect FAIL** (`pytest tests/test_store_backend.py -v`: missing columns).
- [ ] **Step 3: Implement** `backend.py` and move every `sqlite3` call in `store.py` behind `Conn`. In `evidence._canon` drop the key `actor_id` when its value is `None`, so pre-team events hash as before.
- [ ] **Step 4: Run `pytest -q`, expect all pass** (213 + 3).
- [ ] **Step 5: Commit** `feat(store): pluggable back end and identity columns`.

### Task 2: Project and person scope in the store

**Files:**
- Create: `harness/team/__init__.py`, `harness/team/principal.py`
- Modify: `harness/audit/store.py`
- Test: `tests/test_store_scope.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Principal: id: str; name: str; email: str | None; kind: Literal["person", "token", "service", "typed"]`. `id` format: `oidc:<issuer>#<sub>`, `token:<token_id>`, `service:<name>`; `typed` principals have `id = ""`.
- Produces: `AuditStore.scoped(project: str | None, principal: Principal | None) -> AuditStore` sharing the back end. A scoped store stamps `runs.project` and `runs.started_by_id` in `start_run`, `items.created_by_id` in `add_item`/`edit_item`, `events.actor_id` in `log_event`. It filters `list_runs`, `items_of_type`, `latest_decisions`, `find_answer` and `events(run_id=None)` to its project by joining `runs`. Unscoped (personal mode) behaves as today; rows with `project IS NULL` belong to project `None`.
- Produces: `AuditStore.run_project(run_id: str) -> str | None`; `AuditStore.touched_by(item_id: str, actor_id: str) -> bool` (any version's `created_by_id` equals it); `AuditStore.started_by(run_id: str) -> str | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_projects_are_walls(tmp_path):
    # a = store.scoped("brake", P1); b = store.scoped("body", P2)
    # a.start_run + add finding; b.items_of_type("finding") == []; b.list_runs() == []
    # b.latest_decisions() has no item from a

def test_replay_never_crosses_projects(tmp_path):
    # log a "generated" event in project a; b.find_answer(same hashes) is None; a.find_answer is not None

def test_scoped_writes_stamp_project_and_person(tmp_path):
    # run row project == "brake", started_by_id == P1.id; event actor_id == P1.id;
    # edited item version created_by_id == P1.id; touched_by(item, P1.id) is True, P2 False

def test_job_thread_keeps_scope(tmp_path):
    # pass the scoped store into threading.Thread, log_event inside it,
    # event has project's run and actor_id == P1.id
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** scope as two attributes on `AuditStore` (`_project`, `_principal`) copied by `scoped()`; a private `_run_filter()` returning the SQL fragment and args.
- [ ] **Step 4: Run `pytest -q`, expect all pass.**
- [ ] **Step 5: Commit** `feat(store): project walls and person stamps`.

### Task 3: Team settings and the data rule

**Files:**
- Create: `harness/team/settings.py`
- Modify: `harness/config.py` (`HarnessConfig.team`), `harness/models/runner.py` (line ~125, next to the offline check), `harness/bench.py:39`, `pyproject.toml` (`team` extra)
- Test: `tests/test_team_settings.py`

**Interfaces:**
- Produces (pydantic, in `settings.py`): `ProjectSettings(name: str, rule_profile: str = "default", four_eyes: bool = True, roles: dict[Literal["viewer","engineer","approver"], list[str]])`; `OidcSettings(issuer: str, client_id: str, client_secret: str, groups_claim: str = "groups", scopes: list[str] = ["openid","profile","email"])`; `ServiceAccount(project: str, role: str, token_sha256: str)`; `TeamSettings(database_url: str, public_url: str, session_secret: str, session_hours: int = 10, oidc: OidcSettings, admins: list[str], projects: dict[str, ProjectSettings], allowed_models: list[str], service_accounts: dict[str, ServiceAccount] = {}, token_days: int = 90)`.
- Any string value `env:NAME` is read from the environment at load; a missing variable fails load with "Team setting needs environment variable NAME".
- Produces: `HarnessConfig.team: TeamSettings | None = None`; `HarnessConfig.is_team() -> bool`; `HarnessConfig.model_allowed(profile_name: str) -> bool` (personal mode: true unless offline blocks it; team mode: name in `allowed_models`, empty list means none).
- `pyproject.toml`: `team = ["psycopg[binary]>=3.2", "authlib>=1.3", "itsdangerous>=2.1"]`; add `team` to `all` and `dev`.

- [ ] **Step 1: Write the failing tests**

```python
def test_env_indirection_and_missing_env(monkeypatch, tmp_path): ...
def test_model_not_allowed_is_refused_before_sending(cfg_team, audit):
    # structured_call with a profile outside allowed_models raises before FakeProvider.calls grows,
    # and an event action "model_refused" with detail {"profile": ...} is logged
def test_empty_allowed_models_means_offline(cfg_team): ...
def test_personal_mode_unchanged(cfg): assert cfg.team is None and cfg.model_allowed("fake-gen")
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Add a `cfg_team` fixture to `tests/conftest.py` built from fake profiles, two projects (`brake`, `body`) and groups `g-brake-eng`, `g-brake-appr`, `g-body-view`, `g-admin`.
- [ ] **Step 4: Run `pytest -q`, expect all pass.**
- [ ] **Step 5: Commit** `feat(team): settings, team extra and the data rule`.

### Task 4: Permissions and the four-eyes rule

**Files:**
- Create: `harness/team/permissions.py`
- Test: `tests/test_permissions.py`

**Interfaces:**
- Consumes: `Principal`, `TeamSettings`, `AuditStore.touched_by`, `AuditStore.started_by`.
- Produces: `ACTIONS = ("view", "run", "edit", "decide", "admin")`; `ROLE_ACTIONS = {"viewer": {"view"}, "engineer": {"view","run","edit"}, "approver": {"view","run","edit","decide"}}`; admin group members get `"view"` and `"admin"` on every project; `"run"`, `"edit"`, and `"decide"` require a project role.
- Produces: `@dataclass(frozen=True) class Verdict: ok: bool; reason: str | None`.
- Produces: `@dataclass(frozen=True) class Access: principal: Principal; roles: dict[str, str]; admin: bool` (project -> highest role). People and personal tokens get it from groups: `access_for_groups(principal: Principal, groups: list[str], team: TeamSettings) -> Access`; a service account gets `Access(principal, {its project: its role}, False)`. Personal mode uses `PERSONAL_ACCESS`, which allows everything.
- Produces: `can(access: Access, project: str, action: str) -> Verdict`; `can_decide(access: Access, item: dict, audit: AuditStore, team: TeamSettings) -> Verdict` (role first, then four-eyes when the project's `four_eyes` is true).
- Four-eyes: refuse with "You edited this; someone else must decide on it." when `audit.touched_by(item_id, principal.id)`; refuse with "You started this run; someone else must decide on its findings." when `item["item_type"] == "finding"` and `audit.started_by(item["run_id"]) == principal.id`.
- Role refusal reason: "Your role on this project is {role}; deciding needs approver." (and the matching text for run/edit: "...; this needs engineer.").

- [ ] **Step 1: Write the failing tests:** a table test over (groups, project, action) -> ok; `test_service_account_limited_to_its_project_and_role`; `test_four_eyes_editor_refused`, `test_four_eyes_run_starter_refused_on_findings_only`, `test_four_eyes_off_allows_self`, `test_admin_sees_every_project`, `test_no_group_no_projects`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `feat(team): roles per project and the four-eyes rule`.

### Task 5: PostgreSQL back end and `zyn upgrade`

**Files:**
- Create: `harness/audit/pg.py`, `harness/audit/migrations.py`
- Modify: `harness/audit/store.py` (URL detection), `harness/__main__.py` (`upgrade` command)
- Test: `tests/test_store_pg.py`, and parametrise `tests/test_store_backend.py` and `tests/test_store_scope.py` over back ends

**Interfaces:**
- Produces: `PostgresBackend(url: str)` implementing `Backend`; converts `?` to `%s`; `claim_lock()` uses `SELECT pg_advisory_xact_lock(hashtext(?))` on the claim key; ids via `BIGSERIAL ... RETURNING`.
- Produces: `migrations.MIGRATIONS: list[tuple[int, str, list[str]]]` (version, label, SQL for each back end); table `schema_versions(version INTEGER, applied_at TEXT, label TEXT)`; `current_version(backend) -> int`; `upgrade(admin_url: str, app_user: str) -> list[int]` applies missing versions, creates the append-only triggers (PL/pgSQL `RAISE EXCEPTION '<table> is append-only'`) and runs `GRANT SELECT, INSERT` plus sequence `USAGE` to `app_user`, and nothing else.
- Produces: CLI `zyn upgrade --admin-url URL --app-user NAME` (URL may also come from `ZYN_DATABASE_ADMIN_URL`); prints applied versions.
- Produces: the server refuses to start in team mode when `current_version < latest` with "Database schema is version N, this Zyn needs M. Run: zyn upgrade".
- Test database: tests use `ZYN_TEST_PG_URL` (admin rights on a throwaway database); without it, PostgreSQL tests are skipped with reason "set ZYN_TEST_PG_URL to run PostgreSQL tests". Add `pgserver` to the `dev` extra and a `tests/pg_fixture.py` that starts one when `ZYN_TEST_PG_URL` is unset and `pgserver` imports; if it cannot start on this platform, skip with that reason.

- [ ] **Step 1: Write the failing tests:** every store test from Tasks 1 and 2 runs on both back ends; `test_app_user_cannot_update_or_delete` (connect as the app user, UPDATE and DELETE fail on every table); `test_upgrade_is_idempotent`; `test_server_refuses_old_schema`.
- [ ] **Step 2: Run, expect FAIL (or SKIP if no PostgreSQL; then start one before continuing).**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `pytest -q` with a PostgreSQL available, expect all pass and no PostgreSQL skips.** Record in the commit message whether PostgreSQL tests actually ran.
- [ ] **Step 5: Commit** `feat(store): PostgreSQL back end and zyn upgrade`.

### Task 6: `zyn import-log`

**Files:**
- Create: `harness/team/importlog.py`
- Modify: `harness/__main__.py`
- Test: `tests/test_import_log.py`

**Interfaces:**
- Produces: `import_log(sqlite_path: Path, target: AuditStore, project: str) -> dict` returning `{"runs": n, "items": n, "events": n, "skipped_runs": [run_id, ...], "event_offset": k}`. Copies rows unchanged, including `ts`; sets `runs.project = project`; identity columns stay NULL. A run ID already present in the target is skipped and listed, never overwritten. `event_id`s are kept when none collide (`event_offset` 0); otherwise every imported `event_id` is shifted by `k` = (highest `event_id` in the target), so several personal logs can share a project. Each import logs one `log_imported` event with `{"file_sha256", "event_offset", "runs"}`, so an evidence pack exported before the move can be matched to the team log (its own chain still verifies from the file, as `evidence.verify_chain` reads only the file). After copying on PostgreSQL, the events sequence is moved past the highest `event_id`.
- Produces: CLI `zyn import-log FILE --project P` (needs `--admin-url` like `upgrade`, because it writes explicit ids).

- [ ] **Step 1: Write the failing tests:** `test_import_keeps_ids_and_evidence_head` (first import: evidence `audit_chain` head before == after), `test_import_twice_skips_runs`, `test_second_log_shifted_and_offset_logged` (two logs both starting at event 1 land in one project; `log_imported` records the offset; an evidence file exported from the second log before import still passes `verify_chain`), `test_imported_rows_have_no_actor_id`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `pytest -q`, expect all pass.**
- [ ] **Step 5: Commit** `feat(team): import a personal audit log into a project`.

### Task 7: Sign-in, sessions and tokens

**Files:**
- Create: `harness/team/auth.py`, `harness/team/tokens.py`
- Modify: `harness/api/server.py` (`create_app`, `who()`), `harness/audit/migrations.py` (tokens table)
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces: `class IdentityProvider(Protocol)`: `login_redirect(request) -> Response`, `async callback(request) -> Claims`; `OidcProvider(settings: OidcSettings, public_url: str)` using `authlib.integrations.starlette_client`; `FakeIdentityProvider(claims: Claims)` for tests. `Claims = TypedDict(sub, iss, name, email, groups)`.
- Produces: `create_app(cfg, audit=None, idp: IdentityProvider | None = None)`. In team mode routes `/auth/login`, `/auth/callback`, `/auth/logout`; `SessionMiddleware(secret_key=team.session_secret, max_age=team.session_hours*3600, https_only=True, same_site="lax")`; every `/api/*` route except `/api/health` needs a principal, else 401 `{"error": "Sign in first."}`.
- Session stores only `principal` fields and a `signed_in_at`. Groups are not trusted from the session: every request re-reads the person's latest groups from the latest `signed_in` event (`detail.groups`), so removing a group takes effect at the next sign-in, and an admin can force it by revoking with `zyn revoke-person <id>` (logs `person_revoked`; sessions older than it are rejected). Each sign-in logs `signed_in` with `actor_id`, name, email, groups.
- Produces: `tokens` table `(token_id TEXT, sha256 TEXT, owner_id TEXT, owner_name TEXT, label TEXT, created_at TEXT, expires_at TEXT)`; `create_token(audit, owner: Principal, label: str, days: int) -> tuple[str, str]` returning `(token_id, secret)` where the secret is shown once; `revoke_token(audit, token_id, by: Principal)` logs `token_revoked`; `resolve_token(audit, team, secret) -> Principal | None` (checks hash, expiry, not revoked; principal kind `token`, acting with the owner's current groups). Service accounts resolve from `team.service_accounts` by hash, with their configured project and role.
- Produces: `who(request: Request, data: dict) -> Access` (from Task 4). Team mode: session or bearer token. Personal mode: `Access(Principal(id="", name=typed, email=None, kind="typed"), {}, True)` from `data["reviewer"]` as today, with the same 403 message. Handlers pass `access.principal.name` wherever they pass `actor` today.
- Requests carrying `Authorization: Bearer <secret>` use tokens; cookie sessions need the header `X-Zyn-Request: 1` on writes (CSRF guard; the web client sends it).

- [ ] **Step 1: Write the failing tests:** `test_api_needs_sign_in_in_team_mode` (401), `test_personal_mode_still_uses_typed_name`, `test_callback_creates_session_and_logs_signed_in`, `test_group_removed_takes_effect_after_next_sign_in`, `test_revoked_person_session_rejected`, `test_token_works_until_revoked_or_expired`, `test_service_account_token_scoped_to_its_project`, `test_cookie_write_without_header_refused`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `pytest -q`, expect all pass.**
- [ ] **Step 5: Commit** `feat(team): company sign-in, sessions and access tokens`.

### Task 8: Authorisation on every route, views with reasons, health

**Files:**
- Modify: `harness/api/server.py`, `harness/api/views.py`, `harness/__main__.py`
- Test: `tests/test_api_team.py`

**Interfaces:**
- Consumes: `who() -> Access`, `can`, `can_decide`, `AuditStore.scoped`, `run_project`.
- Files stay in their project: uploads go to `runs/uploads/<project>/`; `/api/download` in team mode takes `run_id` and `path`, and serves only files under `runs/exports/<run_id>/` of a run in the person's project (404 otherwise). Uploads over `team.max_upload_mb` (new `TeamSettings` field, default 50) answer 413 "File is over N MB."
- `AuditStore.decide(item_id, decision, actor, comment=None, extra: dict | None = None)`: `extra` is merged into the event detail; in team mode the server passes `{"four_eyes": <project setting>}` on every decision, so the log shows which rule applied.
- Every request in team mode resolves a project: query parameter `project` or body field `project`, defaulting to the first project the person can view. Handlers use `audit.scoped(project, principal)`. Any `run_id` or `item_id` whose run's project differs answers 404 "No run" / "No such item", the same as a missing one.
- `run`, `new`, `action` need `run`; `edit` needs `edit`; `decide` needs `can_decide`; `bulk` applies `can_decide` per item and returns `{"ok": true, "count": n, "skipped": [{"item_id", "reason"}]}`.
- `views.decision_state(audit, item, scope=None, block_approve=None, block_decide: str | None = None)`: when `block_decide` is set every decision button is disabled with that reason. Card builders accept and pass a `rights: Callable[[dict], Verdict]`; personal mode passes one that always allows.
- New checks for `check start` in team mode use the project's `rule_profile` unless the request names one.
- `/api/config` adds `version`, `mode: "personal" | "team"`, `person: {name, email} | null`, `projects: [{id, name, role, four_eyes}]`, `project: str | null`, `admin: bool`.
- `GET /api/team-settings` (admin only): the loaded `TeamSettings` with every secret and token hash replaced by "set" or "missing", plus the rule profiles in the Zyn folder. Read-only: in this version IT changes settings and rule profiles as files in the Zyn folder, under its own change control.
- `/api/health` (no sign-in): `{"status": "ok", "version": __version__, "mode": ..., "schema": n}`.
- `views.audit_view` shows actor as name plus "(name typed, not signed in)" for team-mode events with no `actor_id` that are not model actors.
- CLI: in team mode only `serve`, `upgrade`, `import-log`, `revoke-person`, `where` and `remote` run; every other command prints "This Zyn folder is a team server. Use zyn remote, or the review screen." and exits 2.

- [ ] **Step 1: Write the failing tests:** `test_other_project_ids_are_404` (run, item, audit, download, decide, edit, action), `test_download_outside_run_exports_is_404`, `test_upload_over_limit_is_413`, `test_decision_records_four_eyes_setting`, `test_team_settings_admin_only_and_secrets_masked`, `test_viewer_cannot_start_or_edit` (403 with the role reason), `test_engineer_cannot_decide`, `test_four_eyes_on_decide_and_bulk_skips`, `test_card_shows_block_decide_reason`, `test_project_rule_profile_used`, `test_config_lists_only_my_projects`, `test_health_without_sign_in`, `test_cli_refuses_in_team_mode`, `test_typed_name_label_in_audit_view`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `pytest -q`, expect all pass, including the untouched `tests/test_api.py`.**
- [ ] **Step 5: Commit** `feat(team): project walls and roles on every route`.

### Task 9: Review screen in team mode

**Files:**
- Modify: `web/src/lib/api.ts`, `web/src/lib/reviewer.tsx`, `web/src/screens/Shell.tsx`, `web/src/screens/common.tsx`, `web/src/components/Decision.tsx`, `web/src/App.tsx`
- Create: `web/src/screens/SignIn.tsx`, `web/src/screens/PersonMenu.tsx`, `web/src/screens/Tokens.tsx`
- Modify: `docs/design-system.md` (new patterns: person menu, project switcher, disabled-with-reason for roles), `zyn-identity/` only if a glyph is missing (build with `zyn-identity/tools/build.py`)
- Test: `web/src/components/ui.test.tsx` additions, `tests/test_design_system.py` passes

**Interfaces:**
- Consumes: `/api/config` fields from Task 8, `/auth/login`, `/auth/logout`, token endpoints `POST /api/tokens {label}` -> `{token_id, secret}`, `GET /api/tokens`, `POST /api/tokens/{id}/revoke` (add these three routes to `server.py` in this task, team mode only, any signed-in person, own tokens only).
- `mode === "team"`: no reviewer box; sidebar shows the person menu (name, role on the current project, project switcher, "Access tokens", "Sign out"); writes send `project` and header `X-Zyn-Request: 1`; a 401 shows the sign-in page ("Sign in with your company account", one primary button to `/auth/login`). The project in use is kept in the URL (`?project=`).
- Disabled decision buttons show `block_decide` / role reasons as tooltip and inline text, as `block_approve` does today.
- Admins get a read-only "Team settings" view from `/api/team-settings`. Every mode shows the Zyn version in the sidebar footer.
- Tokens screen: list (label, created, expires, revoked), "Create token" shows the secret once with a copy button and "You will not see this again."; empty state "No tokens yet. Create one for scripts and test benches."
- `mode === "personal"`: no visible change.

- [ ] **Step 1: Write failing component tests** for: person menu renders name and role; decision button disabled with the four-eyes reason; sign-in page on 401; personal mode still shows the reviewer box.
- [ ] **Step 2: Run `npx vitest run`, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `npx vitest run`, `npx tsc -b`, `npx vite build`, `pytest -q`; expect all pass.**
- [ ] **Step 5: Look at the screen** in team mode (fake sign-in server from Task 7 tests exposed by `zyn serve --team --fake-sign-in NAME,GROUPS` available only when `ZYN_DEV=1`) and personal mode, light and dark, desktop and phone width; test clicks against a copy of the audit database. Screenshot each.
- [ ] **Step 6: Commit** `feat(web): sign-in, person menu, projects and tokens`.

### Task 10: `zyn remote` for scripts and test benches

**Files:**
- Create: `harness/team/remote.py`
- Modify: `harness/__main__.py`
- Test: `tests/test_remote.py`

**Interfaces:**
- Produces: `zyn remote --server URL [--project P] <command>` with token from `ZYN_TOKEN`; commands `runs`, `check FILE [--source SPEC] [--rules R]`, `testcheck TESTS... --dbc DBC [--reqs SET]`, `delta OLD NEW`, `findings RUN_ID` (JSON to stdout), `export RUN_ID --as-file PATH`. Each maps to the existing `/api/new/{kind}`, `/api/runs`, `/api/runs/{id}`, `/api/download` routes. Exit code 0 on success, 1 when the check found open findings and `--fail-on-findings` is given, 2 on any API error with its message printed.
- Uses `httpx` (already a dependency of `anthropic`; add `httpx>=0.27` to core explicitly).

- [ ] **Step 1: Write failing tests** against `create_app` through `httpx.ASGITransport`: `test_remote_check_starts_run_in_project`, `test_remote_fail_on_findings_exit_code`, `test_remote_bad_token_exit_2`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run `pytest -q`, expect all pass.**
- [ ] **Step 5: Commit** `feat(team): zyn remote for automation`.

### Task 11: Container, logs and the IT guide

**Files:**
- Create: `Dockerfile`, `compose.yaml`, `compose.trial.yaml`, `deploy/team.example.yaml`, `docs/wiki/Team-server.md`
- Modify: `harness/__main__.py` (`serve --team --host`), `harness/api/server.py` (JSON access log in team mode), `docs/wiki/_Sidebar.md`, `docs/wiki/Roadmap.md`, `README.md` (one line linking the guide)
- Test: `tests/test_container_files.py`

**Interfaces:**
- `Dockerfile`: `python:3.11-slim`, installs the wheel from `dist/` with the `team` extra, runs as a non-root user `zyn`, `ZYN_HOME=/data`, `EXPOSE 8600`, `HEALTHCHECK` on `/api/health`, `CMD ["zyn", "serve", "--team", "--host", "0.0.0.0", "--no-browser"]`.
- `compose.yaml`: `zyn` (volume `/data`, env file) and `postgres:16` (volume), with a one-shot `zyn-upgrade` service using the admin URL.
- `compose.trial.yaml`: adds Keycloak with a realm file containing two synthetic users and the example groups, for trying sign-in without company IT.
- `zyn serve --team`: binds to `--host` (default `127.0.0.1`); refuses `0.0.0.0` in personal mode with "Personal mode only listens on this machine."
- Logs: one JSON line per request with time, method, path, status, duration, principal id, project. No request bodies, no file contents.
- `Team-server.md` (for IT): requirements; install with compose; sign-in setup for Microsoft Entra ID, Okta and Keycloak (redirect URI `<public_url>/auth/callback`, groups claim); the two database users; HTTPS through a reverse proxy (forwarded headers, cookie `secure`); backup and restore with `pg_dump`/`pg_restore` and why the database is the audit record; upgrade steps; the data rule; where data goes (nowhere outside the customer except the allowed model endpoints).

- [ ] **Step 1: Write failing tests:** files exist; Dockerfile runs as non-root and has a HEALTHCHECK; `team.example.yaml` loads with `TeamSettings` when its `env:` variables are set; `serve` refuses `0.0.0.0` in personal mode.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement and write the guide.**
- [ ] **Step 4: Run `pytest -q`, expect pass.** If Docker is available, run `docker compose -f compose.yaml -f compose.trial.yaml up`, sign in as each trial user, and check roles and four-eyes by hand; screenshot. If Docker is not available on this machine, say so in the commit message and the hand-off: the container is unverified.
- [ ] **Step 5: Commit** `feat(team): container, trial sign-in and IT guide`.

---

## After the last task

Run the full checks from Global Constraints, then a whole-branch review. Do not push to GitHub; publishing follows the clean-copy rule.
