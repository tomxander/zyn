# Review of 03a999f..b07ce9d: fixes needed

Date: 2026-11-14. Reviewer: Claude (Claude Code), with three independent review passes (model connectors; J1939, vTESTstudio and weak words; licence, release, CI and copy). Commits reviewed: 8118f13, 782cdcd, b631fa1, 4f2ba10, 94b997a, b07ce9d.

**State:** 358 tests pass with PostgreSQL, ruff clean, web and site build. The tests pass because no test covers the paths below. "Proved" means a probe reproduced it; probes are in the reviewer's scratch folder, not the repo.

**Way of working:** fix in batch order, one commit per batch (F, then G, then H). Every finding gets a test that failed before the fix. Run the full suite with `ZYN_TEST_PG_URL` set (PostgreSQL tests must not skip), `ruff check harness tests evals`, and in `web/` and `site/` the builds. After each batch commit, post the commit hash and test count. Do not start anything outside this list. Do not push anything to GitHub: publishing is done separately as a clean snapshot.

Copy rules for everything you write (docs, site, README, messages): no "proves", "verifies", "guarantees", unqualified "pass"/"clean" (use "no flag" or "no code-check findings"), "any model", "enterprise-ready", or savings percentages. The team server is "built, not yet proven" until a person signs in to Zyn through a real provider in the container. No em dashes.

## Batch F: model connectors (782cdcd)

1. **Offline mode bypass through `local: true`.** Proved. `harness/models/runner.py:196` accepts `local` on any provider and with any value; `{provider: openai, model: gpt-4o, local: true}` with no base_url sent data to api.openai.com in offline mode, and a Bedrock profile with `local: true` called us-east-1. `local: "false"` (a string) also counts as local.
   - Allow `local` only for provider `openai`, only as a strict boolean.
   - Require base_url to resolve to loopback, private (RFC 1918, fc00::/7) or link-local addresses, or to a host on an admin list (`offline_allowed_hosts` in config). Refuse otherwise, before any network call, logged as `blocked_offline` with the reason.
   - Apply the same host rule to Ollama's `host` (today any host counts as local), and refuse Ollama `-cloud` models in offline mode.
   - Record on the `generated` event that the offline exemption was used and why.
   - Update Team-server.md's air-gap section to match.
2. **Provider construction errors escape unlogged.** Proved. `get_provider(profile)` at runner.py:204 is outside the try; Azure with no key, Bedrock with no boto3 or no region (raw BotoCoreError), Vertex errors raise past every caller and the API answers 500 with no event. Build the provider inside the failure path, map every construction error to `ProviderError`, log `provider_error`.
3. **Vertex `UnboundLocalError` without google-auth.** Proved. vertex_provider.py:314 reads `google` after its import failed. Give a clear install message.
4. **Malformed responses escape as AttributeError / JSONDecodeError, unlogged.** Proved. openai_provider.py:352,361,364, azure_provider.py:105,116-117 (`.get` on None or list), bedrock_provider.py:215 (`json.loads` unguarded). Guard the parsing, and in runner.py catch any non-ProviderError from `generate()` and log it as `provider_error` so every attempt is logged.
5. **Credentials leak into the audit store and API errors.** Proved. openai_provider.py:318-344 embeds raw `base_url` (with `user:password@`) and `resp.text[:500]` in errors that land in detail_json and the 400 response. Strip userinfo and query strings from any URL in messages; cap and scrub upstream bodies (drop anything that looks like a key or Authorization value). Send the Gemini API key in the `x-goog-api-key` header, not `?key=` (vertex_provider.py:342). Restrict `api_key_env` to names that do not match Zyn's own secrets (`ZYN_*`, `SESSION_SECRET`, `DB_PASSWORD`, `OIDC_SECRET`).
6. **Bedrock Converse does not constrain output to the schema.** Proved. bedrock_provider.py:236-251 sends no schema. Use toolConfig with one forced tool carrying the schema; map stopReason `max_tokens`, `guardrail_intervened`, `content_filtered`; take `model_served` from the response where given.
7. **Bedrock Anthropic warns "served model differs" on every call.** Proved. Compare against the Bedrock model id correctly (strip the `anthropic.` and region prefixes) so the warning only fires on a real mismatch.
8. **Bedrock request shape.** Inferred: `output_config` (bedrock_provider.py:190) is likely rejected by the example `anthropic.claude-3-5-sonnet-20241022-v2:0`. Send only keys Bedrock InvokeModel accepts for Anthropic models; use the forced-tool route for structure. Region must be required, not silently us-east-1 (data residency).
9. **Vertex request shape.** Proved what is sent, inferred what fails: `responseSchema` with `additionalProperties`/`anyOf null` (use `responseJsonSchema` for JSON Schema), `location: global` builds `global-aiplatform.googleapis.com` (should be `aiplatform.googleapis.com`), the `gemini-` prefix is added to non-Gemini models (`gemma-3-27b-it`). Take `model_served` from `modelVersion`; count `thoughtsTokenCount`; map `SAFETY` and `RECITATION` finish reasons to a refusal, not three validation retries.
10. **OpenAI and Azure fields for reasoning models.** Send `max_completion_tokens`, and omit `temperature` for models that reject it (o-series, gpt-5 family) or when the profile says so. Map `message.refusal` and `content_filter` to a refusal instead of retrying.
11. **bench.py and `zyn profiles` disagree with the runner.** Proved. bench.py:41,54 refuses a valid local vLLM profile offline and reports a keyless Azure profile ready; `__main__.py:62` labels the four new providers "test only". Use one readiness function for all three.
12. **No install extras.** Add `bedrock = ["boto3>=1.34"]`, `vertex = ["google-auth>=2.30"]`, include both in `all` and `dev`, and decide whether the team container installs them (document it). The light install must stay unchanged.
13. **Tests mostly check their own mocks.** Add tests that assert the actual request body and headers for each provider (with `httpx.MockTransport` and a fake boto3 client that records calls), runner integration tests for offline, `allowed_models` and `local` with each new provider, and tests for findings 1 to 5. Clear `GOOGLE_CLOUD_PROJECT` and `VERTEX_BEARER_TOKEN` in tests.

Docs: wherever these connectors are mentioned (README, Roadmap, Team-server, site), say "built, not tried against live endpoints". Team-server.md:19 must not list them as working endpoints.

## Batch G: J1939, vTESTstudio and weak words (b07ce9d, 4f2ba10)

1. **`j1939_null_source` fires on every message of a standard J1939 DBC.** Proved. Public J1939 DBCs use source address 0xFE as "any sender" (EEC1 0x0CF004FE). Do not flag 0xFE in a DBC; never flag PGN 60928 (Address Claimed / Cannot Claim is sent from 0xFE by rule). If kept at all, report it once per file, grouped.
2. **`j1939_dlc_exceeded` fires on valid multi-packet PGNs.** Proved. DM1, VI, SOFT and similar are defined at full length and carried by the Transport Protocol. Treat a length over 8 as valid multi-packet (up to 1785 bytes) and report one fault per message, not two.
3. **Detection treats any mostly-29-bit DBC as J1939.** Proved: GMLAN `gm_global_a_lowspeed_1818125.dbc` in opendbc now gets 2 false findings; a proprietary 29-bit battery DBC got 5. Decide J1939 from the DBC itself: `ProtocolType "J1939"` or per-message `VFrameFormat J1939PG` (cantools `Message.protocol == 'j1939'`). Run the J1939 checks per message on those messages only. No guessing from ID width.
4. **J1939 attributes never read.** Proved. `getattr(db, "protocol")` is always empty. Covered by G3. Read the `SPN` attribute where present.
5. **`j1939_standard_id`** flags 11-bit frames, which J1939 networks may carry (proprietary frames). Drop it, or make it advice that says so; the text "SAE J1939 requires 29-bit extended identifiers" overstates the standard.
6. **Bit 25 is the Extended Data Page bit**, not "reserved", since J1939-21 (2006). Rename the check or drop it; fix the module docstring (j1939.py:3), which claims SPN and priority checks the code does not do.
7. **vTESTstudio tests pass silently on other layouts.** Proved (outside.py:174-178,188): child-element layouts miss out-of-range values; attribute order picks the wrong number (`wait="100"` before `value="9500"`); checks inside `<!-- -->` count as checks; a `<title>` child means no test case is found and the whole file becomes one unit; `.VTT` upper case is not matched. Parse the XML with a real parser (`xml.etree`, defusedxml-safe settings), strip comments, read values by attribute or child name, match suffixes case-insensitively, and when no test case is recognised, refuse the file with a reason (no silent pass).
8. **Greedy name pattern** reads `classname=`/`displayname=` or the last `title=` as the test name, giving false `duplicate_name`. Fixed by G7's parser; add the test.
9. **Weak-word exceptions hide real vague wording.** Proved: "as required by the driver", "as required in the current situation", "within the normal range", "operate at normal voltage", "return to normal mode" are no longer flagged. Narrow the exceptions to the real standard terms only (e.g. "as required by ISO/IEC/SAE/UN ECE <number>", "Fast Ethernet", "fast charging"), move them into the configurable allow-list in `harness/sift/rules.py` instead of hard-coding them in checks.py, and document them in Checks-reference.md. Re-run the S5 code-checks-only row on QuRE and update Benchmarks.md and README if the numbers move.
10. **Docs for the new checks.** Add the J1939 categories to `dbc_check.py`'s docstring, `docs/wiki/Checks-reference.md`, `docs/wiki/Anvil-Review.md` and `harness/checklist.py` DBC_CHECKS. Add `.vtt .vts .vxt` to the test file picker in `web/src/screens/NewRun.tsx:111` and its label. Update Roadmap.md: J1939 and vTESTstudio are "first checks built, tried on synthetic and public files only", not done.

## Batch H: release, CI, licence and copy (8118f13, 94b997a, b631fa1)

1. **release.yml cannot pass its own tests.** Proved: installs only `.[team]`, so 7 test modules fail to import streamlit, and test_sift needs python-docx. Install `.[dev]` (or `importorskip` those tests) and run the PostgreSQL tests with a postgres service container and `ZYN_TEST_PG_URL`, as the Release guide claims.
2. **The wheel build fails.** Proved with setuptools 65.5.0 under `--no-build-isolation`: `license-files` rejected. Upgrade pip and setuptools in the job before building (setuptools>=77) and raise `requires` in pyproject accordingly. Fail the job if `web/dist` is missing (setup.py only warns today) and if the tag does not equal `v` + the pyproject version.
3. **The Release guide tells you to push local history.** Proved. GitHub gets clean snapshots only. Rewrite the publishing steps: build the snapshot from `git archive HEAD` into the clone of tomxander/zyn, commit there, tag that snapshot commit, push from the clone. Never `git push` from the working repo.
4. **The Docker trial check never signs in to Zyn.** Proved by reading. Add a real sign-in in verify-trial-docker.sh: follow `/auth/login` to Keycloak, post alice's credentials to the Keycloak login form, follow the redirect to `/auth/callback`, keep the session cookie, then call a signed-in `/api/...` endpoint and check the person and project. Until that passes in CI, docs keep "built, not yet proven"; Team-server.md:46-51 must not call the current script an end-to-end test.
5. **verify-trial-docker.sh can wipe a real trial.** `down -v` without a project name: use `-p zyn-verify-$$` (or similar) everywhere. Also `grep -q "(healthy)"` at :48, `cd "$(dirname "$0")/.."` at the start, mark the script executable in git (`git update-index --chmod=+x`), and check upgrade has exited, not just running, at :62.
6. **Keycloak direct grant** may be refused: set `directAccessGrantsEnabled` explicitly in deploy/trial-realm.json if the script keeps using it.
7. **Workflow tokens.** `persist-credentials: false` on checkout, permissions at job level (`contents: write` only on the release job's publish step), pin softprops/action-gh-release to a commit SHA, `permissions: contents: read` on docker-trial.yml, include the workflow file in its own path filter.
8. **LICENSE factual problems** (fix these; leave legal completeness to a lawyer, see below):
   - :26 "PRIVACY GUARANTEE" uses a banned word and :27 claims the software "operates locally or within your private network", untrue when a cloud model is configured. Reword to what is true: Zyn sends nothing to its makers; model calls go only to the endpoints the customer configures; offline mode refuses cloud calls.
   - Add `THIRD_PARTY_NOTICES.md` listing bundled third-party code and assets with their licences (fonts under SIL OFL in site/public/fonts and zyn-identity/fonts; the npm packages bundled into web/dist with their MIT/ISC/Apache notices, generated from web/package-lock.json; Python dependencies are not bundled). Ship it in the wheel and the container. State in LICENSE that third-party components keep their own licences.
   - pyproject: add `license = "LicenseRef-Proprietary"` and classifier `Private :: Do Not Upload`.
   - Dockerfile:85: copy LICENSE and THIRD_PARTY_NOTICES.md so the image carries them.
9. **The site bundles every wiki page**, including unlisted ones (Release guide with its git instructions). Load only the pages listed in DOCS in site/src/docs/docs.ts.
10. **Copy breaches** (fix all, in the files named):
    - README.md:8 tagline: use "AI writes the work. Zyn checks it before you sign." README.md:73 "prove", :156 "any model", :183 "Quotes verified by code" (say "Quotes located by code").
    - docs/wiki/FAQ.md:25 "any model Ollama serves"; Team-server.md:163 "Security guarantees", :173 "engineered for regulated automotive safety (ISO 26262, ASPICE)".
    - site/src/sections/Hero.tsx:55 "shows you what was changed, invented or weakened": say "flags".
    - site/src/content.ts:171 "one shared record nobody can edit": say the running app can only add records; :75 "the history can't be quietly changed": qualify for desk mode (the record refuses edits and deletes; the evidence export's hash chain shows any change); :7, :122 soften "every" and "any"; :139-140, :231 unqualified "pass"/"passed"; :228 "clean result".
    - site/src/sections/Teams.tsx:53-54: add the "built, not yet proven" caveat in that section.
11. **Lower:** bump Node to 22 LTS in release.yml and Dockerfile; Release-guide.md:13 must match what CI actually runs.

## Batch I: follow-ups found when re-checking Batch F (fe7a559)

Batch F closed the offline leak; these remain (all proved by probe unless marked):

1. **DNS can change between the check and the call.** security.py:102 resolves once; httpx resolves again to connect. A DNS server answering private then public gets past offline mode. Connect to the checked address (pinned transport or resolver hook), keeping the original Host header and TLS server name.
2. **Proxy settings bypass the host rule.** httpx honours `HTTP_PROXY`/`HTTPS_PROXY`; with a proxy set, the checked private host was approved but the connection went to the proxy. In offline mode use `trust_env=False`, or run the proxy host through the same rule.
3. **`offline_allowed_hosts` does nothing.** Neither HarnessConfig nor TeamSettings has the field, so load_config drops it; runner.py:135-137 and readiness.py:33-35 always see empty. Add the field to the config model, validate it, test it, and keep Team-server.md:178 accurate.
4. **Wildcard and metadata addresses allowed.** Refuse `0.0.0.0`, `::`, and the cloud metadata address `169.254.169.254` (and `fd00:ec2::254`); keep other link-local allowed only if documented.
5. **`models_match` over-corrected** (security.py:115-146): `gpt-4o` vs `gpt-4`, `gpt-4o` vs `gpt-4o-mini`, `llama3:70b` vs `llama3:8b` all count as the same model. Normalise only provider prefixes (Bedrock `anthropic.`, region prefixes like `us.`, `eu.`) and version/date suffixes; a different size or family must warn.
6. **`scrub_error_text` misses bare keys** such as `sk-proj-...`, `sk-ant-...`, `AKIA...`, `AIza...`. Redact those patterns too.
7. Minor: readiness reports a local vLLM profile "ready" without reaching it; say "configured" unless a reachability check ran.

Found when re-checking Batch G (51f9bc9):

8. **EDP/DP check is inverted** (j1939.py:126). Per SAE J1939-21 (2006 on): EDP=0/DP=0 page 0, EDP=0/DP=1 page 1, EDP=1/DP=0 "SAE J1939 reserved", EDP=1/DP=1 "ISO 15765-3 defined". Flag EDP=1/DP=0 only; fix the comment (ISO 15765-2 fixed addressing uses EDP=0).
9. **Single-line (minified) vTESTstudio XML gets false findings on every test** (`no_setup` because the one line contains "expected"; test names flagged `unknown_signal`). When the XML parser is used, build each test's checks from the parsed elements, not from source lines.
10. **Values written as element text are missed** (`<teststep signal="EngineSpeed">9500</teststep>`), silently, when another step in the test is read from attributes. Read value attributes and element text alike.
11. **Namespaced XML** loses names (`find("title")`, `attrib.get("name")` ignore namespaces) and falls back to line matching. Match on local names.
12. **Nested test cases are checked twice** (Outer and Inner report the same value). Check each step once, under its innermost test case.
13. **Over-refusal:** `<!DOCTYPE` inside a comment is refused; UTF-16 files are refused with "invalid token". Detect encoding from the BOM / XML declaration, and check for DOCTYPE/ENTITY declarations after parsing with a parser that forbids them (defusedxml-style), not by text search.
14. **Weak-word allow pattern too wide** (rules.py:44): "as required by SAE standards" and "as required by en route timing" are suppressed. Require a standards body as a whole word followed by a document number (e.g. `ISO 26262`, `SAE J1939-21`, `UN ECE R10`).
15. **Length check on J1939 messages:** only lengths over 1785 are flagged, so a 9-byte single-frame PGN is accepted. Allow over-8 lengths only for PGNs known or declared multi-packet (DBC length over 8 is the declaration; a 9-byte message defined as 9 is fine, but flag lengths between 9 and 1785 only when the DBC also marks the message single-frame, otherwise leave as is and document the trade-off).
16. **Published numbers:** re-run S5 code-checks-only on QuRE and update Benchmarks.md, README and the site if it moved (reviewer estimates 55 of 80 becomes about 54 of 79). Roadmap: say J1939 and vTESTstudio checks were tried on synthetic files only (no public J1939 DBC or real vTESTstudio file was available). Rename `j1939_null_source` to `j1939_global_source` to match what it now means.
17. **Intermittent test failure.** `tests/test_forge.py::test_exported_tests_run_on_the_simulated_bench` failed once in a full run at b606555 and passed in the next two full runs and alone. Likely a shared path or port when another process runs at the same time. Find the shared resource (temp folder, export path, port) and make the test use its own `tmp_path`.

## Batch J: follow-ups found when re-checking Batch H (b606555)

Checked from a fresh `git archive HEAD`, as CI will see it.

1. **AuditStore mishandles `sqlite:///` URLs** (harness/audit/store.py:69-70): the whole URL goes to `Path`. On Windows it becomes the drive-relative `C:Users\...` and works only when the current folder is on another drive; on Linux it opens a new empty `sqlite:/tmp/...` database. Parse the URL properly (`sqlite:///relative`, `sqlite:////absolute`, Windows `sqlite:///C:/...`), refuse anything else with a clear message, and test on both forms. `tests/test_api_team.py::test_team_server_opens_team_database_url` and `::test_revoke_person_cli_requires_as_and_records_actor` fail from a clean archive.
2. **Tests that need git-ignored data:** `tests/test_pack.py::test_manifest_pins_every_file_and_marks_tasks_ready` and `::test_export_writes_inspect_and_promptfoo_files` need `data/public/promise/nfr.arff`. Skip with a clear reason when the public data is absent (`pytest.mark.skipif`), or use a small synthetic fixture. CI must pass from a clean checkout.
3. **release.yml:88 pins a commit SHA that does not exist** (`c062e49c...`). Re-pin `softprops/action-gh-release` to the real SHA of a real tag, taken from `git ls-remote https://github.com/softprops/action-gh-release refs/tags/v2.*`, with the tag in a comment.
4. **Release guide snapshot step keeps deleted files:** before extracting `git archive HEAD` into the clone, remove everything in the clone except `.git` (`git rm -rq .` then extract, then `git add -A`).
5. **Trial sign-in check too weak** (verify-trial-docker.sh:159): assert alice's project `bcm` and her `approver` role in `/api/config`, not just the `"projects":` key. Write `cookies.txt` to a `mktemp` file.
6. **THIRD_PARTY_NOTICES.md** is hand-written and misses 19 production packages from web/package-lock.json (the @floating-ui packages, aria-hidden, react-remove-scroll and its helpers, use-callback-ref, use-sidecar, get-nonce, detect-node-es, motion-dom, motion-utils, esm-env, js-tokens, loose-envify, radix-ui, tslib under 0BSD). Generate the npm section from the lock file with a script in `scripts/` (name, version, licence, copyright from each package's LICENSE), and add a test that every production package in the lock file is listed. Fix the Plex reserved font name ("Plex") and do not claim the fonts ship in the wheel or image (they do not).
7. **Remaining copy:** README.md:184 "which checks passed or failed", :185 "It is never passed.", :273 "checks that passed or failed", README.md:298 and docs/wiki/Home.md:44 "Nothing is verified until...", docs/wiki/Research-basis.md:42 "Quotes are verified by code". Use "flagged / no flag", "approved", "located by code".
8. Minor: Release guide lints `evals/` but CI does not; make them match (lint `harness tests evals` in CI).

## Batch K: follow-ups found when re-checking Batch I (633bbea)

1. **DNS pinning still raceable** (proved). One call resolves the host three times (runner check, `build_offline_transport` check, a third lookup whose `addrinfo[0]` becomes the pin), so the pinned address is never checked. openai_provider.py:37 swallows a failed check and falls back to an unpinned transport; a pin lookup that raises does the same. Do one lookup, check every address it returned, pin to an address from that same lookup, pass it from the runner to the provider, and raise (logged `blocked_offline`) when anything fails. No unpinned fallback in offline mode.
2. **Ollama is not pinned** (proved): only `trust_env=False` was added; the client resolves the host again. Give the Ollama client the same pinned transport (it accepts httpx client arguments). The readiness check's `ollama.Client` also needs `trust_env=False`.
3. **Pinned pool drops settings:** keep `verify` (allow a CA bundle path in the profile for corporate CAs), `limits`, `retries` and `http2` from the normal client.
4. **`models_match` still loose:** `deepseek-v2` vs `deepseek-v3` and `mistral-large-2407` vs `-2411` match, and an empty served name counts as a match. Do not strip `-vN`; treat different dated releases as different (warn); empty served name: record "not reported", no match.
5. **Prefixed XML namespaces still fall back to line matching** (proved, `xmlns:v` / `v:testcase`): each test is cut out without the root's namespace declarations. Parse the whole document once and walk the tree, or carry the declarations into each fragment. A misspelt signal in a prefixed-namespace file must be caught.
6. **New silent pass** (proved): `_ops` returns the XML result even when empty, so a step vocabulary the parser does not know (`<set sig="EngineSpeed">9500</set>`) gives 0 findings where 51f9bc9 caught 9500. When the parser reads no steps from a test that has step-like elements, fall back to line matching or flag the test as "steps not read" (no silent pass). Add the test.
7. **Anvil-Review.md:24** still says "both set to 1" for the EDP/DP check; fix to EDP=1, DP=0.
8. **J1939 length trade-off** (I15): nothing reads a single-frame mark; a 9-byte EEC1 is accepted. Document the trade-off in Anvil-Review.md and Checks-reference.md (or remove the misleading code comment).
9. **S5 re-run (I16) not done.** Re-run the S5 QuRE code-checks-only row with the current checks and update Benchmarks.md, README and site if it moved. If the run needs data that is not present, say so in the commit message instead of guessing.
10. **Intermittent full-suite failures (I17) not done.** A full run at 633bbea failed once and passed on the next run, after test_forge failed once at b606555. Run the suite several times, find the test and the shared resource, and fix it.
11. Low: link-local addresses other than the metadata ones (fe80::, 169.254.x) are still allowed offline; document that they are treated as local.

## Batch L: last follow-ups (re-checks of 97cc2f7 and 393684e)

Confirmed fixed: single-lookup DNS pinning with no unpinned fallback, Ollama pinned, pool settings kept, sqlite URL parsing, data-dependent tests skip, action SHA real, snapshot step clears the tree, notices complete and generated, prefixed namespaces, EDP/DP doc, J1939 length doc. The S5 re-run gives the published 0.31 / 0.35, 55 of 80 unchanged.

1. **`models_match` over-corrected** (proved): `gpt-4o` vs `gpt-4o-2024-08-06`, `gemini-2.5-pro` vs `-002`, `claude-sonnet-4-5` vs `-20250929`, `llama3` vs `llama3:latest` now warn on every normal call. Match when the served name is the requested name plus only a date or build suffix (`-YYYY-MM-DD`, `-YYYYMMDD`, `-NNN`, `:latest`); keep `-vN`, size and variant suffixes as mismatches.
2. **`offline_allowed_hosts` ignores IP addresses** (proved): the IP-literal check runs before the allow-list. Check the allow-list first (documented: the admin list overrides).
3. **CI fails on a clean checkout** (proved): `test_serve_fake_sign_in_authenticates` gets 503 because release.yml runs pytest before building web/dist. Build the web screen before the tests.
4. **Trial script cleanup never runs** (proved): the new `trap 'rm -f "${COOKIE_FILE}"' EXIT` replaces `trap cleanup EXIT`, so `docker compose down -v` never runs. Delete the cookie file inside `cleanup()` and remove the second trap. Also check that the `bcm` project entry carries the `approver` role (parse the JSON with python or jq), not two loose substrings.
5. **Release guide first snapshot:** `git rm -rq --ignore-unmatch .`
6. **Notices generator defaults:** a package with no licence in the lock file must fail the generator, not default to MIT; a missing copyright line must be reported, not filled with "contributors".
7. **vTESTstudio unknown step tags** (proved, `<stimulate channel="EngineSpeeed">`): a misspelt signal in a tag the parser does not know gets no `unknown_signal`, plus a false `no_setup`; single-line unknown tags give a false `no_setup`. When the parser falls back for a test, run the line-based name and setup checks for that test too.
8. **README:** :185 "It is never approved." is wrong (approval is a person's act); say "It is never reported as no flag." Update the tests badge (:29) to the current count from a clean run. Tidy :184.

## Batch M: final follow-ups (re-check of 1cd2206)

1. **Trial script role check always fails** (proved): verify-trial-docker.sh reads `d.get('projects', {}).get('bcm', [])`, but `/api/config` returns `projects` as a list of `{"id": "bcm", "role": "approver", ...}` (harness/api/server.py:395-415). Use `any(p.get("id") == "bcm" and p.get("role") == "approver" for p in d["projects"])` and the jq form `.projects[] | select(.id=="bcm" and .role=="approver")`. tests/test_container_files.py:215 asserts the wrong expression: make it test the behaviour (run the one-liner against a sample `/api/config` body in the real shape).
2. **`models_match` matches in reverse:** a profile naming a fixed snapshot (`gpt-4o-2024-08-06`) served by the moving alias (`gpt-4o`) counts as a match. Only allow the served name to add a suffix to the requested name, not drop one.
3. **`offline_allowed_hosts`:** accept bracketed IPv6 entries (`[2606:4700::1111]`), and never allow the cloud metadata addresses (`169.254.169.254`, `fd00:ec2::254`) even when listed.
4. **README tests badge:** say the number of tests that pass in a full run with PostgreSQL on a clean checkout, or drop the count.

## For Tom, not for Antigravity

The licence needs a lawyer before any customer sees it: who the Licensor is, a contributor agreement (the site invites code), defined terms, term and termination, governing law, liability cap, confidentiality. An AI should not draft these.

## Checked and correct

- allowed_models is checked before offline and before any provider is built; both refusals are logged; replay sends nothing. Profiles are never serialised into the API or the audit store. Azure header, deployment URL and api-version support strict json_schema. Imports are lazy; the light install is unchanged.
- PGN extraction (PDU1, PDU2, data page, priority, SA) is correct. Published opendbc numbers and showcase S1 still hold. Weak-word change does no harm on QuRE human labels (false alarms 107 to 95, no lost true flags) but hides real vague wording elsewhere (G9).
- Workflows are valid YAML with current action versions; the web build runs before the wheel; the Docker trial job really builds and starts compose and checks /api/health. No secrets in workflows. Datasets: no licence conflict (public data is git-ignored). No employer or original-product references, no em dashes in added lines.
