# Online demo

The real review screen (`web/src`, unchanged) running in a browser with no server. `mock.ts` stands in for the
Python API: it answers the screen's `/api` calls from recorded runs and applies decisions in memory. A reload starts
fresh; nothing is stored or sent.

Published with the website at `/zyn/demo/` (built by `site`'s `build` and `build:thomasalex` scripts, through
`vite.demo.config.ts`).

## What works and what doesn't

| Works | Declines, with a "needs Zyn on your machine" message |
|---|---|
| Browse the three runs, filters, requirements, audit log | Running the AI reviewer, stability passes, extraction |
| Confirm, dismiss and reopen, with the server's own rules (blocked approvals, reason needed over an AI objection) | Edits, bulk approval, new runs from your own files |
| Export and evidence: the real files Zyn made from these runs | Scoring against an answer key |

Exports are the files as recorded, so they do not include decisions made in the demo. The demo note says so.

## Where the data comes from

- `fixtures/`: API answers recorded with Starlette's `TestClient` from a **copy** of the audit log, for three runs on the
  synthetic ICX-100 set: Sift Review `20261113-235738-c3d95c` (code checks and AI reviewer), Sift Delta
  `20261113-175302-b02846` (revision 1 to 2), Anvil `20261113-182131-30ee1c` (template tests).
- `public/demo-files/`: the real Export and Evidence outputs of those runs.

Before recording, the copy was cleaned: reviewer names became "Demo reviewer" and machine paths became repo-relative.
The append-only triggers were dropped on the copy only, to allow that. Exports were then generated from the cleaned copy
in the git-ignored `runs/demo-home`, so the evidence report's hash chain still verifies.

## Regenerating

1. Copy `runs/audit.sqlite` into a scratch Zyn folder (config, rules, `data/synthetic`, `taxonomy_placeholder.yaml`)
   under `runs/demo-home`, and replace names and paths in the copy.
2. With `ZYN_HOME` pointing at that folder, record `GET /api/config`, `/api/runs`, `/api/runs/<id>` and
   `/api/runs/<id>/audit`, and call `POST /api/runs/<id>/actions/export` and `.../evidence` with reviewer
   "Demo reviewer". Save the action answers as `fixtures/actions.json`.
3. Copy `runs/demo-home/runs/exports/*` into `public/demo-files/`, and keep only the three demo runs in `config.json`'s
   run lists.
4. Check `fixtures/` and `public/demo-files/` for names and machine paths before committing.

Type-check with `npx tsc -p tsconfig.demo.json`.
