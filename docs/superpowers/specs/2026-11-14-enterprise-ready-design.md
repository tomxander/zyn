# Zyn enterprise ready: design

Date: 2026-11-14. Status: ready for Tom's approval.

## Intent

Sell Zyn to vehicle manufacturers, passenger and commercial, through a company Tom is part of. Adoption runs through the people who use it every day: **requirement engineers and test engineers who review specifications and test cases daily**. Engineers try it first; their team and their IT department then have to accept it.

Zyn stays what it is: the checker for AI-made (or human-made) engineering work. Code checks decide what they can prove, an AI reviewer advises with quoted evidence, and a named person makes every decision in an append-only audit log. Enterprise ready means a manufacturer can run that inside its own walls, for a whole team, with the models it chooses.

## Goals

1. A team at a manufacturer can run Zyn on its own servers or in its own cloud account (VPC), with company sign-in, roles and a shared audit log.
2. The customer chooses the models: local models on their hardware, or frontier models through access they already have (Anthropic, AWS Bedrock, Google Vertex, Azure, OpenAI-style endpoints such as Azure OpenAI or vLLM).
3. It fits the daily work of requirement and test engineers: specs in, findings reviewed, results back into their requirement tool and test bench.
4. It gives a buyer the evidence they need to trust it: engineer-reviewed results, a tool-qualification kit, security documents.

## Non-goals (for now)

- A hosted online service run by Zyn's makers.
- Scribe (documents) and Source (procurement).
- Generating more output. Generation stays as a feature; the product is review.
- Running many server copies behind a load balancer. One server per customer site.

## Anti-goals (a failure even if it works)

- Any customer data, telemetry or usage reaching Zyn's makers without the customer turning it on.
- The AI approving anything, or a decision without a signed-in person behind it.
- Breaking the single-PC install that engineers use to try Zyn.
- Mixing the code for team mode and personal mode so far that every change must be made twice.

## Constraints

- Build on the existing code; no rewrite. Rules stay in Python (`harness/api/views.py`, enforced again in `harness/api/server.py`); the screen only shows them.
- Every new screen element follows `docs/design-system.md` and the Zyn identity icons.
- Public or synthetic data only in the repository, demos and tests.
- GitHub gets clean snapshots, never the local history.

## Approaches considered

- **A. Team ready first, then a pilot.** Build the team server and model connectors, then pilot with a real team; daily-workflow fit and the trust pack follow. Slower to first outside user, but removes IT's most likely "no": unapproved tool, personal laptop, no sign-in.
- **B. Pilot first, build what it asks.** Fastest learning, but real specs rarely go into an unapproved tool, so the pilot stalls or runs on toy data, and the product bends to one customer.
- **C. Rebuild as a hosted platform.** Works against on-premise, customer-chosen models and keeping what works.

**Chosen: A, plus showing the single-PC version to engineers early** on public and synthetic data while the team server is built (Tom's decision).

## The programme: four projects and one parallel track

Each project gets its own design and plan, in this order. Only project 1 is designed in detail here.

| # | Project | Done when |
|---|---|---|
| 0 | **Show engineers early** (parallel) | 5 to 10 requirement or test engineers have used `zyn demo` and the code checks on sample or public data, and their reactions are written down |
| 1 | **Team server** | A team signs in with company accounts on a server in their own network or cloud, with roles and a shared audit log |
| 2 | **Model connectors** | An admin points Zyn at Bedrock, Vertex, Azure or an OpenAI-style endpoint by configuration, and can forbid anything else |
| 3 | **Daily-workflow fit** | A requirement set and its review state go round trip with a requirement tool; a spec revision lands in Sift Delta; test reviews cover CANoe CAPL and vTESTstudio |
| 4 | **Trust pack** | An engineer-reviewed answer key, a tool-qualification kit (intended use, limits, evidence) and a security pack (architecture, data flows, questionnaire answers, software bill of materials) |

A pilot with a real team starts once projects 1 and 2 are done. J1939 checks for commercial vehicles join project 3.

### Project 0: show engineers early

- Material: the light install, `zyn demo`, and a short script of what to try (check a requirement set against its spec, check tests against a CAN database).
- Data: ICX-100 synthetic and the public sets already in the repository. Never the engineer's own company data.
- Record per engineer: role, what they tried, what they would use daily, what stopped them, which requirement tool and test bench they use. Keep in a simple tracker outside the repository.
- Feeds the order of work in project 3.

## Project 1: team server, in detail

### What a team gets

```
Company sign-in  ->  Zyn team server (their network or VPC)  ->  shared audit log (their database)
                          |                                      uploads and exports (their storage)
                          +-> model endpoint the admin allowed
```

One install, run by the customer's IT: a container image plus a compose file (Zyn and a database), also runnable as `zyn serve --team` on an ordinary server.

### Two modes, one codebase

- **Personal mode** (today): one PC, typed reviewer name, SQLite file, listens on this machine only. Unchanged.
- **Team mode**: switched on in config. Sign-in required for every request, reviewer identity comes from the sign-in, never typed. The difference lives in one place: the function that answers "who is acting" (today `who()` in `harness/api/server.py`) and a role check next to it.

### Sign-in

- Company single sign-on through OpenID Connect, which covers Microsoft Entra ID, Okta, Ping, Keycloak and most others.
- The audit log records the person's stable ID and their display name and email at the time of the action.
- Sessions in secure cookies; sign-out; session length set by the admin.
- SAML: not in the first version (builder's note: add if a pilot's IT requires it).

### Roles (my proposal)

| Role | Can |
|---|---|
| Viewer | Read runs, findings, the audit log; download exports |
| Engineer | Everything a viewer can, plus start checks, upload files, run the AI reviewer, edit items |
| Approver | Everything an engineer can, plus confirm, dismiss, approve, reject and reopen |
| Admin | Settings: models allowed, the data rule, rule profiles, project membership |

Roles come from the company's sign-in groups, mapped in config, so IT manages people in the place they already do. Every role rule is computed and enforced in Python; the screen shows disabled actions with the reason.

### Projects (separating programmes)

Runs belong to a **project** (a vehicle programme or team). A person sees only projects their groups grant. Personal mode has one implicit project. (My proposal; manufacturers keep programmes apart.)

### Shared database

- PostgreSQL in team mode, SQLite stays for personal mode. The store keeps one interface; both back ends pass the same tests.
- Append-only holds on PostgreSQL too: triggers refusing update and delete, and the application's database user granted insert and select only.
- A one-off command moves an existing SQLite audit log into PostgreSQL with its hash chain intact.
- Uploads and exports on a mounted folder in the first version; object storage (S3-compatible) later.

### The data rule

An admin setting lists which model endpoints may be called. Anything else fails before it is sent, and the refusal is logged. "Offline" is the empty list. Zyn sends nothing to its makers: no telemetry, no update checks, no licence calls home.

### Running it

- Health check endpoint, structured logs, version shown in the screen and the API.
- Database schema versions with automatic, logged upgrades; a documented backup and restore (the database is the audit record).
- HTTPS through the customer's reverse proxy or load balancer; documented settings.
- Upload size limits; file paths confined to the storage folder (as today).

### Screen changes

Sign-in page, a person menu (name, role, project, sign out), a project switcher, actions disabled with the reason when the role does not allow them. The typed reviewer box disappears in team mode. All per the design system, every state covered.

### Tests

- Each role rule, in both modes, against the API.
- A fake sign-in provider in tests; no real company account needed.
- The store test suite run against SQLite and PostgreSQL.
- The existing 213 tests keep passing in personal mode.

### Decisions from the builder check (Claude's calls, for Tom to check)

1. **Roles are set per project.** Someone can approve on one programme and only view another. Every permission check takes the project as an input from the start. Sign-in groups map to (project, role) pairs.
2. **Projects are walls.** Everything that reads across runs today gets a project filter: calibration, learning, carrying over earlier decisions, duplicate checks, and replay of stored AI answers. An AI answer computed on one programme's spec is never reused on another. Rule profiles are the one shared thing, and an admin chooses which profile each project uses.
3. **The command line goes through the server in team mode.** No typed names. Each person can create a personal access token; admins can create service accounts for automation (CI, test benches), each with a project and role. Direct writes to the team database from the command line are refused.
4. **Moving a personal log keeps old evidence verifiable.** Event IDs and timestamps are copied unchanged, so evidence packs exported before the move still check out. A stored, continuously checked hash chain is a new feature and goes to project 4 (trust pack).
5. **Team settings live in a config file that IT manages.** Allowed models, the data rule, the group-to-role mapping and the projects are all in the file, so IT can keep it in its own change control. The screen shows them read-only to admins. In the first version the admin role sees settings, all projects and the full audit log; rule profiles are files in the Zyn folder that IT changes, and the screen lists them. Editing settings in the screen comes later, with an audit event for every change.
6. **Upgrades use a separate database user.** `zyn upgrade` runs at deploy time with a user that may change tables; the running server uses the insert-and-select-only user. Documented for IT.
7. **Imported personal logs go into a project named on the command, one file at a time.** Several files can go into the same project. Typed names are kept and shown as "name typed, not signed in", so the record never pretends they were verified.

### Four-eyes rule (Tom's decision)

A setting per project, **on by default**: a person may not approve, reject or confirm an item they created or edited, or a finding on a run they started. The check is computed in Python and enforced again in the server; the screen shows the disabled action with the reason ("You edited this; someone else must approve it"). Switching it off is an admin setting in the config file, and the audit log records each decision with the setting that applied. In personal mode the setting is off, since there is one person.

## Left to the builder

- Libraries for sign-in, sessions and PostgreSQL access, and how the store interface is split.
- Container base image, compose layout, configuration format for team settings.
- Order of work inside project 1, as long as personal mode never breaks.
- Exact screen layout of the new elements, within the design system.

## Open questions for Tom

None left for project 1. Projects 2 to 4 get their own design rounds.
