# Zyn: instructions for any UI work

The review screen is a React app in `web/` served by the Python API in `harness/api/` (`python -m harness serve`, or `.\review.ps1`). The old Streamlit screen (`harness/review/`, `.\review-classic.ps1`) is legacy: no new features there.

Any change that adds or alters something a person sees (a screen, a tab, a card, a button, a message, a new tool such as Scribe or Source) follows the Zyn design system:

- Read [docs/design-system.md](docs/design-system.md) first. It sets the principles, libraries, hierarchy, tokens, motion, components, patterns and the 10-step process for new UI.
- Rules live in Python: checks, blocked approvals and reasons are computed in `harness/api/views.py` and enforced again in `harness/api/server.py`. The screen only shows them.
- Build from the components in `web/src/components/`. Colours, fonts, sizes and durations live only in `web/src/styles/tokens.css`; animation timings only in `web/src/components/motion.ts`.
- A new visual pattern goes into the components and the docs first, in the same change.
- Icons come only from the Zyn identity set (`zyn-identity/`, served by `web/src/components/icons.tsx`). A missing meaning gets a new glyph built with `zyn-identity/tools/build.py` in the same grid grammar; never a stock icon library.
- Cover every state: empty, loading, read-only without a reviewer name, disabled with a reason, failed, done.
- One primary button per card or tab. One status badge per card. Status in words as well as colour. Calm motion only.
- Copy: sentence case, named actions, counts in labels, say who said it (code check or AI reviewer), no em dashes.
- Before calling it done: `.\.venv\Scripts\python -m pytest -q` (includes tests/test_design_system.py and tests/test_api.py), `ruff check harness tests`, in `web/`: `npx tsc -b` and `npx vite build`; then look at the screen in light and dark at desktop and phone width. Test clicks against a copy of the audit database, not `runs/audit.sqlite`.
