# Development

## Checks before calling anything done

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check harness tests evals
```

In `web/`:

```powershell
npx tsc -b
npx vite build
```

Then look at the screen in light and dark, at desktop and phone width. Test clicks against a copy of the audit database, never `runs/audit.sqlite`.

The tests run offline with a fake model provider; no key is needed.

## The review screen

- `npm install` once in `web/`, then `npm run build` (output in `web/dist`, served by `python -m harness serve`).
- For live editing: `python -m harness serve --no-browser` and `npm run dev` (port 5173, calls the API on 8600).

## Design system

Every new screen, tab, card, button or message follows [docs/design-system.md](../design-system.md):

- Build from the components in `web/src/components/`.
- Colours, fonts, sizes and durations live only in `web/src/styles/tokens.css`; animation timings only in `web/src/components/motion.ts`.
- Icons come only from the identity kit. A missing meaning gets a new glyph in the same grid grammar, never a stock icon.
- Cover every state: empty, loading, read-only, disabled with a reason, failed, done.
- One primary button per card or tab. One status badge per card. Status in words as well as colour.
- Copy: sentence case, named actions, counts in labels, say who said it, no em dashes.

`tests/test_design_system.py` enforces the rules it can.

## Identity kit

Edit `zyn-identity/tools/build.py`, run it, render PNGs with `node tools/render.cjs`, check with `tools/validate.py`, then copy `icons/zyn-sprite.svg` to `web/src/assets/`.

## Conventions

- Prompts are versioned files in `harness/prompts/`. Never edit a released prompt; add `_v2`.
- Old runs keep their original workflow IDs; the screen maps them to today's tool names.
- Python 3.11. Pinned versions in `requirements.lock`.
