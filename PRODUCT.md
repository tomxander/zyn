# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Tom first, later automotive software engineers. They review AI-produced engineering items in long desk sessions, often hundreds of items at a time: requirements extracted from specifications (Sift), findings on an existing requirement set (Sift Review), test specs and generated cases (Anvil), and changes between specification revisions (Sift Delta). The job is to decide each item (approve, reject or edit) quickly and with the evidence in view.

## Product Purpose

Zyn is a model-agnostic checker and benchmark for automotive engineering work. Models propose; code checks the proposals; an independent AI reviewer gives advice; a named person decides. Success is a reviewer getting through a large set fast without trusting anything the evidence does not support.

## Positioning

Nothing counts until a named person decides. Code checks are shown as checks, not as model confidence. The AI reviewer is advice and can never approve. Every action is written to an append-only audit log, and undoing a decision adds a record rather than erasing one.

## Operating Context

Daytime desk work at a monitor, in a bright room, for long sessions. Windows, local only: the Python API and the React screen run on the same machine (`python -m harness serve`, `.\review.ps1`). Inputs are specifications (PDF, DOCX, Markdown), requirement sets (ReqIF, Excel, CSV) and CAN databases (DBC). Outputs are JSON, Excel, ReqIF and pytest exports plus the audit log.

## Capabilities and Constraints

- Tools: Sift, Sift Review, Sift Delta, Anvil (formerly Forge; old runs keep "forge" as an alias). Scribe and Source are planned.
- Public or synthetic data only; no company or customer documents.
- Label: "Zyn prototype." on every screen. Outputs are unverified until a named reviewer approves them.
- Offline mode must keep working: no required network calls at runtime.
- Rules (checks, blocked approvals, override reasons) live in Python and are enforced by the API; the screen only shows them.
- Gold data is author-made and AI-reviewed, not engineer-reviewed; say so wherever scores appear.

## Brand Commitments

- Name: Zyn. Tool names Sift, Anvil, Scribe, Source.
- Voice: plain, declarative, sentence case, no em dashes, no motivational filler.
- Colour: near-monochrome (confirmed 2026-11-13). The accent marks the one primary action, focus and the current tab; status colours appear only as small marks and text, never as tinted blocks or banners.
- Must not feel like a generic SaaS dashboard, and must not feel spreadsheet-cramped (confirmed 2026-11-13).

## Evidence on Hand

Real runs in `runs/audit.sqlite`: the ICX-100 instrument cluster specification (synthetic) with Sift, Sift Delta and Anvil runs; Sift Review runs on a public sample set (`sample_200_42.csv`, 405 findings); PROMISE and RTEMS evaluation runs. Synthetic data lives in `data/synthetic/`. No customer names, logos or testimonials exist and none may be invented.

## Product Principles

1. The item and its evidence come first; everything else is secondary.
2. Speed of judgement over speed of clicking: every decision is one key or one click, and undoable.
3. Honesty about the machine: model output is labelled as advice, checks as checks.
4. Calm over a long session: nothing competes for attention that does not need a decision.

## Accessibility & Inclusion

WCAG 2.2 AA: 4.5:1 text contrast, 3:1 for control edges and focus, full keyboard operation, reduced-motion support.
