# Team server review: fixes needed

Date: 2026-11-14. Reviewer: Claude (Claude Code), with three independent review passes (security, data and audit record, screen and container). Code: branch `team-server`, commits 86f9a6f..f68a694. Plan: `docs/superpowers/plans/2026-11-14-team-server.md`.

**State:** 275 tests pass, 2 PostgreSQL tests skipped, ruff clean, `tsc`, `vite build` and 8 screen tests pass. The tests pass because no test covers the paths below. Most findings were proved with probes; "inferred" marks the rest.

**Way of working:** fix in the batch order below, one commit per batch, each finding with a test that failed before the fix. Stop after each batch and post the commit hash and test count, so the reviewer can check it before the next batch. Do not start the unapproved extras (interrupted jobs, SIEM stream, coverage view, ASPICE map, licence file, DLP).

## Batch A: the team server does not use the team database

1. **PostgreSQL is never used.** `create_app` (server.py:127), `revoke-person` (__main__.py:478) and `import-log` open `cfg.resolved_db_path()` (SQLite). `team.database_url` is read nowhere. In team mode every one of these must open `team.database_url`. Proved.
2. **No refusal on an old schema.** The server must refuse to start in team mode when the database is behind (plan Task 5), with the plan's message. `/api/health` must report the database's version, not `MIGRATIONS[-1][0]`.
3. **App user cannot use `tokens`.** migrations.py GRANT omits `tokens`. Every bearer request fails on PostgreSQL. Also nothing creates the app role; either `zyn upgrade` creates it (`--app-password` from env) or the guide and compose do. Inferred.
4. **`claim` does not lock on PostgreSQL.** Autocommit releases `pg_advisory_xact_lock` at the end of its own statement (pg.py:189, 207), so the SELECT-then-INSERT races. Run the claim in one transaction. Inferred.
5. **Import is not atomic.** A failure part-way leaves committed runs that a retry then skips forever (importlog.py:32-113). One transaction for the whole import. Proved.
6. **Import shifts ids when nothing collides, and drops run-less events.** Keep ids when there is no overlap (offset 0); import events with `run_id NULL` too (plan Task 6). `import-log` must require `--admin-url` in team mode. Proved.
7. **One connection per store call on PostgreSQL.** `list_items` calls `status()` per row: hundreds of connections per screen load. Use a pool (`psycopg_pool`) or a per-request connection. Inferred.
8. **The PostgreSQL tests never ran.** PostgreSQL 18 runs on Tom's PC. Parametrise the store tests over both back ends (plan Task 5), add `test_app_user_cannot_update_or_delete` and `test_server_refuses_old_schema`, and make `test_store_pg_basic` independent of test order. Tom will set `ZYN_TEST_PG_URL`; none of this counts as done until those tests pass with no PostgreSQL skips.

## Batch B: access control holes

1. **Four-eyes bypass with a token.** A token's principal id is `token:<id>`, not the owner's id (tokens.py:100-106), so a person edits or starts a run with a token and approves in the browser. The principal id must be the owner's id; keep the token id in a separate field for the audit record. Proved.
2. **`carry_over` decides without decide rights or four-eyes** (server.py:653 -> check.py:505). Needs `can_decide` per finding, skips with reasons like bulk, records `four_eyes`. Proved: an engineer approved a finding on her own run.
3. **Revoking a person does not stop their tokens.** `resolve_token` ignores `person_revoked`. Proved.
4. **Token lifetime uncapped.** `days` from the caller is used as given (36500 days works, 10**9 crashes with a 500). Cap at `team.token_days`. Proved.
5. **Admin upload path traversal.** `project` is not checked against `cfg.team.projects` for admins (server.py:751-759); `../zz` wrote outside the uploads folder. Every project value from a request must be a configured project. Proved.
6. **Cross-project leaks.**
   - `/api/config` lists other projects' run ids in `sift_runs` (unscoped `list_runs`). Proved.
   - `decide` runs the code-check and AI-objection checks before the project wall, so another project's item answers 400 instead of 404. Do the project check first, everywhere. Proved.
   - `/api/jobs/{id}` has no project check. Inferred.
   - The `score` action accepts any server path as `key_path`. Confine it to the project's uploads. Inferred.
7. **`serve --team` without a `team:` block serves personal mode on every network interface, without sign-in** (__main__.py:274). Refuse to start: "serve --team needs a team section in config.yaml." Proved by reading.
8. **`can_decide` fails open for a run with no project** (permissions.py:92-94). Fail closed in team mode. Proved.
9. **Upload limit is checked after the whole file is read**, and same-name uploads overwrite each other. Stream with a running size check; give stored uploads unique names. Inferred.
10. **Smaller points:**
    - The session cookie is `https_only` only when `public_url` is https. The plan says always; allow http only with an explicit trial setting.
    - `zyn remote --token` exposes the token in process lists; use `ZYN_TOKEN` only.
    - Groups, revocations and tokens are found by scanning the whole events table on every request; index or cache per request.

## Batch C: the team screen cannot be used

1. **The old "Enter your name" gate still blocks team mode.** 15 controls still use `disabled={!reviewer}` (NewRun.tsx:83, common.tsx:27,46, SiftView.tsx:63,94,126,129, CheckView.tsx:111,116,128, DeltaView.tsx:114,163, AnvilView.tsx:89,211, RequirementCard.tsx:101). In team mode a signed-in person cannot start, edit, export or bulk-approve. Gate on the server-computed rights instead; `reviewer.tsx` should expose "can act" for both modes.
2. **`project` is never sent.** No API call adds it, so the project switcher does nothing and every new run lands in the first project. Send it on every read and write; drop a stale `?run=` from another project when switching.
3. **Team settings view not wired** (`App.tsx` never passes `onOpenSettings`).
4. **Design system breaches:**
   - Inline px styles and an unregistered `setTimeout` in SignIn, PersonMenu and Tokens.
   - Classes (`stack-sm`, `stack-xs`, `signin-page`, `person-menu`) that do not exist.
   - Role chip in lowercase, with the wrong tone.
   - `docs/design-system.md` not updated with the new patterns (required by CLAUDE.md and the plan).
5. **Tokens screen:**
   - Missing states: no loading or failed state, so an error shows "No tokens yet"; "Active tokens" also lists revoked ones.
   - Copy to the plan: "Access tokens", "Create token", sentence case, no "Copied!" or "e.g.", the empty state as specified.
   - Behaviour: Copy fails on plain http, so give a fallback. Revoke needs a confirmation, and one pending revoke must not disable every Revoke button.
6. **Team mode flashes the personal reviewer box while config loads.** Show the loading state instead.
7. The verbatim four-eyes copy in `team.test.tsx:87` differs from the server's.

## Batch D: the container and the IT guide do not work

1. **The Dockerfile cannot produce a working image:**
   - No `setup.py`, so no bundle. No web build. `config.yaml` is not seeded into `/data`, so `load_config` crashes.
   - It installs from source, while the plan says install the wheel from `dist/`.
   - There is no `.dockerignore`: `node_modules`, `runs/` and `.env` would be copied in.
   - Use a two-stage build: Node builds `web/dist`, then the wheel is built and installed with `[team]`.
2. **Settings names do not match.**
   - Compose sets `ZYN_DATABASE_URL`, `ZYN_SESSION_SECRET` and `ZYN_OIDC_*`, which nothing reads, while `team.example.yaml` expects `DB_PASSWORD`, `SESSION_SECRET` and `OIDC_SECRET`.
   - `env:` only works as a whole value, so `postgresql://zyn:env:DB_PASSWORD@...` keeps the literal text. Support `${NAME}` inside strings, or take the whole URL from one variable.
   - The example config has no `roles` or `profiles`, so validation fails.
   - `allowed_models` uses a model id instead of a profile name, so every call would be refused.
3. **No committed default secrets.** Session secret and database passwords must come from the env file, and start-up must fail when they are missing.
4. **Trial sign-in:**
   - No groups mapper in the realm, so tokens carry no groups.
   - Group paths (`/bcm-leads`) do not match the configured names.
   - The issuer `http://keycloak:8080` cannot be reached from the host's browser.
   - No trial config with `public_url` and a team block.
   - Make `compose.trial.yaml` work end to end on `localhost`.
5. **The IT guide claims what the code does not do:**
   - PKCE is claimed but not set.
   - Logs go to stderr, not stdout as claimed.
   - 401 log lines have no principal.
   - The `evidence verify` restore check is blocked in team mode.
   - The guide has no upgrade steps section.
   - The nginx example assumes host networking.
   - The title has an em dash, and headings are in title case.
6. **No container claim without a run.** Docker is not installed on this PC. The guide and the hand-off must say the container is unverified until someone runs it.

## Checked and correct

- Pre-team evidence chains verify (`_canon` drops a `None` `actor_id`).
- Imported rows have no ids.
- Scoped per-ID reads refuse other projects. Replay never crosses projects.
- The data rule is checked before any provider call and logged. An empty list refuses everything.
- `decide` and `bulk` record `four_eyes`.
- 404 for other-project ids on run, audit, action, edit and download. Downloads are confined to the run's exports.
- `/api/health` needs no sign-in. `/api/team-settings` is admin-only with secrets masked.
- The CSRF header is checked on cookie writes.
- Tokens are stored hashed, with expiry and revocation. Service accounts are limited to their project and role.
- Personal mode is unchanged. The light install gained only `httpx`.
