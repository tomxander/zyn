"""Zyn design system for the review screen: tokens, one stylesheet, and the components.

Rules live in docs/design-system.md. In short:
- Every colour, size, radius, font and duration is a token on :root below. CSS rules use
  var(--zyn-...) only; literal values outside the token blocks fail tests/test_design_system.py.
- Screens (app.py) build UI from the helpers in this file and plain Streamlit widgets. They
  never write inline style= HTML or colour values.
- A new visual pattern is added here as a helper, given a token-only CSS rule, and listed in
  the docs before any screen uses it.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

# ---- vocabulary -------------------------------------------------------------------------

# Each tone has one meaning everywhere. Never pick a tone for looks.
TONES = {
    "ok": "passed a check, confirmed, approved",
    "warn": "needs a person: open, failed check, AI objection",
    "info": "edited, needs action, a link or the current page",
    "bad": "broken: cannot be used as is",
    "muted": "closed with no action: rejected, dismissed",
}
STATUS_TONE = {"approved": "ok", "edited": "info", "proposed": "warn", "rejected": "muted"}

WORKFLOW_NAME = {"sift": "Sift", "sift-check": "Sift Review",
                 "sift-delta": "Sift Delta", "forge": "Anvil", "smoke": "Smoke test"}

# ---- tokens -----------------------------------------------------------------------------

TOKENS_LIGHT = """
:root {
  /* colour: status ink and tint */
  --zyn-ok: #1E9E63;    --zyn-ok-bg: rgba(30,158,99,.10);
  --zyn-warn: #B85E0C;  --zyn-warn-bg: rgba(240,138,36,.12);
  --zyn-info: #1F7FE0;  --zyn-info-bg: rgba(46,155,255,.10);
  --zyn-bad: #C93A3A;   --zyn-bad-bg: rgba(209,67,67,.10);
  --zyn-muted: #6B6E73; --zyn-muted-bg: rgba(120,124,130,.12);
  /* colour: structure */
  --zyn-line: rgba(23,24,26,.09);
  --zyn-ring: #2E9BFF;
  --zyn-shadow: 0 0 0 1px rgba(23,24,26,.06), 0 1px 2px rgba(23,24,26,.04),
                0 2px 4px rgba(23,24,26,.04);
  --zyn-shadow-hover: 0 0 0 1px rgba(23,24,26,.08), 0 1px 2px rgba(23,24,26,.08),
                      0 2px 4px rgba(23,24,26,.06);
  /* type */
  --zyn-font-display: "Space Grotesk", sans-serif;
  --zyn-font-body: Inter, sans-serif;
  --zyn-font-mono: "IBM Plex Mono", monospace;
  --zyn-text-xs: 0.75rem;   /* 11px: meta tags only */
  --zyn-text-sm: 0.8rem;    /* 12px: labels, chips, badges */
  --zyn-text-md: 0.875rem;  /* 13px: captions, quotes, sub-lines */
  --zyn-text-base: 1rem;    /* 15px: item text */
  --zyn-text-lg: 1.35rem;   /* 20px: brand */
  --zyn-text-xl: 1.6rem;    /* 24px: page title */
  --zyn-weight-body: 400; --zyn-weight-label: 500; --zyn-weight-strong: 600;
  --zyn-leading: 1.55; --zyn-leading-tight: 1.2;
  --zyn-measure: 75ch;
  --zyn-quiet: .72;         /* opacity for secondary text */
  /* space: 4px grid */
  --zyn-s1: 2px; --zyn-s2: 4px; --zyn-s3: 6px; --zyn-s4: 8px; --zyn-s5: 10px;
  --zyn-s6: 14px; --zyn-s7: 20px; --zyn-s8: 36px; --zyn-s9: 48px;
  /* radius: concentric, one per level */
  --zyn-r-xs: 3px; --zyn-r-sm: 4px; --zyn-r-md: 6px; --zyn-r-lg: 8px; --zyn-r-xl: 12px;
  --zyn-r-pill: 999px;
  /* motion */
  --zyn-fast: 120ms; --zyn-base: 150ms;
  --zyn-ease: ease-out;
  --zyn-press: .96;
  --zyn-disabled: .5;
  /* layout */
  --zyn-page-width: 1180px;
}
"""

TOKENS_DARK = """
:root {
  --zyn-ok: #3DD68C;    --zyn-ok-bg: rgba(61,214,140,.12);
  --zyn-warn: #F5A04D;  --zyn-warn-bg: rgba(240,138,36,.14);
  --zyn-info: #5CB1FF;  --zyn-info-bg: rgba(46,155,255,.14);
  --zyn-bad: #F57A7A;   --zyn-bad-bg: rgba(240,99,99,.13);
  --zyn-muted: #9A9DA3; --zyn-muted-bg: rgba(154,157,163,.14);
  --zyn-line: rgba(255,255,255,.07);
  --zyn-shadow: 0 0 0 1px rgba(255,255,255,.08), 0 1px 2px rgba(0,0,0,.4);
  --zyn-shadow-hover: 0 0 0 1px rgba(255,255,255,.13), 0 1px 2px rgba(0,0,0,.4);
}
"""

# ---- rules (tokens only) ----------------------------------------------------------------

RULES = """
/* base type */
html, body, .stApp { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
h1, h2, h3, h4 { text-wrap: balance; letter-spacing: -0.01em; }
p, li { text-wrap: pretty; }
.zyn-text, .zyn-quote, .zyn-quiet, .zyn-notice, .zyn-chip, .zyn-badge {
  font-family: var(--zyn-font-body); font-weight: var(--zyn-weight-body);
}
[data-testid="stMetricValue"], [data-testid="stDataFrame"], .zyn-num, code {
  font-variant-numeric: tabular-nums;
}

/* page frame */
[data-testid="stMainBlockContainer"] { max-width: var(--zyn-page-width); padding-top: var(--zyn-s8); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }

/* card: shadow-border, never border plus shadow */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .zyn-head) {
  border-color: transparent !important; border-radius: var(--zyn-r-xl);
  box-shadow: var(--zyn-shadow); transition: box-shadow var(--zyn-base) var(--zyn-ease);
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .zyn-head):hover {
  box-shadow: var(--zyn-shadow-hover);
}

/* filter tags: neutral */
[data-testid="stMultiSelectTagsContainer"] [data-tag] {
  background: var(--zyn-muted-bg) !important; color: inherit !important;
  border-radius: var(--zyn-r-md) !important;
}
[data-testid="stMultiSelectTagsContainer"] [data-tag] * { color: inherit !important; }

/* buttons */
.stButton > button, .stDownloadButton > button {
  font-weight: var(--zyn-weight-label); white-space: nowrap;
  transition: background-color var(--zyn-fast) var(--zyn-ease),
              border-color var(--zyn-fast) var(--zyn-ease),
              color var(--zyn-fast) var(--zyn-ease), scale var(--zyn-base) var(--zyn-ease);
}
.stButton > button:active:not(:disabled), .stDownloadButton > button:active:not(:disabled) {
  scale: var(--zyn-press);
}
.stButton > button:disabled, .stDownloadButton > button:disabled {
  opacity: var(--zyn-disabled); cursor: not-allowed;
}
button:focus-visible, input:focus-visible, textarea:focus-visible,
[role="tab"]:focus-visible, summary:focus-visible {
  outline: 2px solid var(--zyn-ring) !important; outline-offset: 2px;
}

/* stat strip */
[data-testid="stMetric"] {
  background: var(--zyn-muted-bg); border-radius: var(--zyn-r-lg);
  padding: var(--zyn-s5) var(--zyn-s6);
}
[data-testid="stMetricLabel"] p {
  font-size: var(--zyn-text-sm); font-weight: var(--zyn-weight-label); opacity: var(--zyn-quiet);
}

/* tabs */
[data-baseweb="tab-list"] { gap: var(--zyn-s2); }
[data-baseweb="tab"] { padding: var(--zyn-s3) var(--zyn-s5); font-weight: var(--zyn-weight-label); }
[data-baseweb="tab"][aria-selected="true"] { font-weight: var(--zyn-weight-strong); }

/* alerts and expanders */
[data-testid="stAlert"] [data-testid="stAlertContainer"] { padding: var(--zyn-s5) var(--zyn-s6); }
[data-testid="stAlert"] p { font-size: var(--zyn-text-md); }
[data-testid="stExpander"] details { border-color: var(--zyn-line); }
[data-testid="stExpander"] summary p { font-weight: var(--zyn-weight-label); }

/* sidebar */
.zyn-side-label {
  font-size: var(--zyn-text-sm); font-weight: var(--zyn-weight-strong); opacity: var(--zyn-quiet);
  margin: var(--zyn-s7) 0 var(--zyn-s3);
}
.zyn-brand { display: flex; align-items: baseline; gap: var(--zyn-s4); margin: calc(-1 * var(--zyn-s4)) 0 var(--zyn-s2); }
.zyn-brand b {
  font-family: var(--zyn-font-display); font-size: var(--zyn-text-lg);
  font-weight: var(--zyn-weight-strong); line-height: 1; letter-spacing: -0.02em;
}
.zyn-brand span {
  font-size: var(--zyn-text-xs); font-weight: var(--zyn-weight-label); line-height: 1;
  color: var(--zyn-warn); background: var(--zyn-warn-bg);
  padding: var(--zyn-s1) var(--zyn-s3); border-radius: var(--zyn-r-sm);
}

/* section heading inside a tab */
.zyn-section { margin: var(--zyn-s7) 0 var(--zyn-s3); }
.zyn-section b { font-family: var(--zyn-font-display); font-size: var(--zyn-text-base);
                 font-weight: var(--zyn-weight-strong); }
.zyn-section span { display: block; font-size: var(--zyn-text-md); opacity: var(--zyn-quiet); }

/* badge (status) and chip (check, signal) */
.zyn-badge {
  display: inline-flex; align-items: center; white-space: nowrap;
  font-size: var(--zyn-text-sm); font-weight: var(--zyn-weight-strong); line-height: 1;
  padding: var(--zyn-s3) var(--zyn-s5); border-radius: var(--zyn-r-pill);
}
.zyn-chip {
  display: inline-flex; align-items: center; gap: var(--zyn-s2);
  margin: var(--zyn-s1) var(--zyn-s3) var(--zyn-s1) 0;
  font-size: var(--zyn-text-sm); font-weight: var(--zyn-weight-label);
  padding: var(--zyn-s1) var(--zyn-s4); border-radius: var(--zyn-r-pill);
}
.zyn-chip i { font-style: normal; font-weight: var(--zyn-weight-strong); }
.t-ok { color: var(--zyn-ok); background: var(--zyn-ok-bg); }
.t-warn { color: var(--zyn-warn); background: var(--zyn-warn-bg); }
.t-info { color: var(--zyn-info); background: var(--zyn-info-bg); }
.t-bad { color: var(--zyn-bad); background: var(--zyn-bad-bg); }
.t-muted { color: var(--zyn-muted); background: var(--zyn-muted-bg); }

/* card header row */
.zyn-head { display: flex; align-items: center; gap: var(--zyn-s5); flex-wrap: wrap;
            margin-bottom: var(--zyn-s1); }
.zyn-head .zyn-id { font-family: var(--zyn-font-mono); font-size: var(--zyn-text-md);
                    font-weight: var(--zyn-weight-strong); line-height: var(--zyn-leading-tight); }
.zyn-head .zyn-meta { font-size: var(--zyn-text-sm); opacity: var(--zyn-quiet); display: flex;
                      gap: var(--zyn-s3); flex-wrap: wrap; }
.zyn-head .zyn-meta code {
  font-size: var(--zyn-text-xs); padding: var(--zyn-s1) var(--zyn-s3);
  border-radius: var(--zyn-r-sm); background: var(--zyn-muted-bg); color: inherit;
}
.zyn-head .zyn-badge { margin-left: auto; }

/* item text, source quote, secondary text */
.zyn-text { font-size: var(--zyn-text-base); line-height: var(--zyn-leading);
            margin: var(--zyn-s3) 0 var(--zyn-s2); max-width: var(--zyn-measure); }
.zyn-quote {
  font-size: var(--zyn-text-md); line-height: var(--zyn-leading); opacity: .8;
  margin: var(--zyn-s2) 0 var(--zyn-s4); max-width: var(--zyn-measure);
  border-left: 2px solid var(--zyn-line); padding-left: var(--zyn-s5);
}
.zyn-quiet { font-size: var(--zyn-text-md); opacity: var(--zyn-quiet); }

/* page header */
.zyn-page { margin: 0 0 var(--zyn-s6); }
.zyn-page .zyn-kicker { font-family: var(--zyn-font-mono); font-size: var(--zyn-text-md);
                        font-weight: var(--zyn-weight-label); line-height: 1; color: var(--zyn-info); }
.zyn-page h2 { margin: var(--zyn-s3) 0 var(--zyn-s2) !important; padding: 0 !important;
               font-size: var(--zyn-text-xl); }
.zyn-page .zyn-sub { font-size: var(--zyn-text-md); opacity: var(--zyn-quiet); }

/* prototype notice */
.zyn-notice {
  font-size: var(--zyn-text-md); line-height: 1.45; padding: var(--zyn-s4) var(--zyn-s6);
  border-radius: var(--zyn-r-lg); margin: 0 0 var(--zyn-s7);
  color: var(--zyn-warn); background: var(--zyn-warn-bg);
}
.zyn-notice b { font-weight: var(--zyn-weight-strong); }

/* word diff and quoted evidence */
.zyn-del { background: var(--zyn-warn-bg); color: var(--zyn-warn); text-decoration: line-through;
           border-radius: var(--zyn-r-xs); padding: 0 var(--zyn-s1); }
.zyn-ins { background: var(--zyn-ok-bg); color: var(--zyn-ok); border-radius: var(--zyn-r-xs);
           padding: 0 var(--zyn-s1); }
mark { background: var(--zyn-warn-bg); color: inherit; border-radius: var(--zyn-r-xs);
       padding: 0 var(--zyn-s1); box-shadow: inset 0 -2px 0 var(--zyn-warn); }

/* empty state */
.zyn-empty { text-align: center; padding: var(--zyn-s9) var(--zyn-s6);
             border: 1px dashed var(--zyn-line); border-radius: var(--zyn-r-xl); }
.zyn-empty b { display: block; font-family: var(--zyn-font-display); font-size: var(--zyn-text-base);
               font-weight: var(--zyn-weight-strong); line-height: 1.3; margin-bottom: var(--zyn-s3); }
.zyn-empty span { font-size: var(--zyn-text-md); opacity: var(--zyn-quiet); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
"""


def inject() -> None:
    """Load the design system. Call once, right after st.set_page_config."""
    # Follow the theme Streamlit is showing (system setting, or the user's own choice).
    dark = getattr(getattr(st.context, "theme", None), "type", None) == "dark"
    st.markdown("<style>" + TOKENS_LIGHT + (TOKENS_DARK if dark else "") + RULES + "</style>",
                unsafe_allow_html=True)


def _tone(tone: str) -> str:
    if tone not in TONES:
        raise ValueError(f"Unknown tone '{tone}'. Use one of: {', '.join(TONES)}")
    return tone


# ---- components: return HTML (to combine) ----------------------------------------------

def badge(text: str, tone: str) -> str:
    """Status pill. One per card, top right. Text says the status; colour backs it up."""
    return f"<span class='zyn-badge t-{_tone(tone)}'>{escape(text)}</span>"


def status_badge(status: str) -> str:
    return badge(status.capitalize(), STATUS_TONE.get(status, "muted"))


def chip(label: str, tone: str) -> str:
    """Small signal next to content (a check, a count, a recurrence)."""
    return f"<span class='zyn-chip t-{_tone(tone)}'>{escape(label)}</span>"


def chips(items: list[tuple[str, bool]]) -> str:
    """Pass/fail checks: ✓ green or ! amber, always with a label."""
    return "".join(f"<span class='zyn-chip t-{'ok' if ok else 'warn'}'><i>{'✓' if ok else '!'}</i>"
                   f"{escape(label)}</span>" for label, ok in items)


def quiet(text_: str) -> str:
    """Secondary inline text (a location, a lead-in)."""
    return f"<span class='zyn-quiet'>{escape(text_)}</span>"


def diff_html(ops: list) -> str:
    cls = {"delete": "zyn-del", "insert": "zyn-ins"}
    return " ".join(f"<span class='{cls[op]}'>{escape(t)}</span>" if op in cls else escape(t)
                    for op, t in ops)


# ---- components: render directly --------------------------------------------------------

def card_head(ident: str, meta: list[str] | None = None, right: str = "",
              extra: str = "") -> None:
    """First line of every item card: ID in mono, meta tags, status badge on the right.

    Its presence is what gives the surrounding st.container(border=True) the card style.
    """
    tags = "".join(f"<code>{escape(m)}</code>" for m in (meta or []) if m)
    st.markdown(f"<div class='zyn-head'><span class='zyn-id'>{escape(ident)}</span>"
                f"{extra}<span class='zyn-meta'>{tags}</span>{right}</div>",
                unsafe_allow_html=True)


def text(body: str) -> None:
    """The item itself (requirement, finding, spec text). The largest text on a card."""
    st.markdown(f"<div class='zyn-text'>{escape(body)}</div>", unsafe_allow_html=True)


def text_html(body_html: str) -> None:
    """Item text that already carries marks or a diff (escaped by the caller)."""
    st.markdown(f"<div class='zyn-text'>{body_html}</div>", unsafe_allow_html=True)


def quote(body_html: str) -> None:
    """Source evidence under the item text."""
    st.markdown(f"<div class='zyn-quote'>{body_html}</div>", unsafe_allow_html=True)


def page_header(kicker: str, title: str, sub: str = "") -> None:
    """Top of every run view: tool name, what this run is about, provenance line."""
    st.markdown(f"<div class='zyn-page'><div class='zyn-kicker'>{escape(kicker)}</div>"
                f"<h2>{escape(title)}</h2><div class='zyn-sub'>{escape(sub)}</div></div>",
                unsafe_allow_html=True)


def section(title: str, hint: str = "") -> None:
    """A heading inside a tab, above a group of cards or a form."""
    st.markdown(f"<div class='zyn-section'><b>{escape(title)}</b>"
                + (f"<span>{escape(hint)}</span>" if hint else "") + "</div>",
                unsafe_allow_html=True)


def notice(label: str) -> None:
    st.markdown(f"<div class='zyn-notice'><b>{escape(label)}</b> Outputs are "
                "model-generated and unverified until a named reviewer approves them.</div>",
                unsafe_allow_html=True)


def brand() -> None:
    st.sidebar.markdown("<div class='zyn-brand'><b>Zyn</b><span>review · prototype</span></div>",
                        unsafe_allow_html=True)


def side_label(text_: str) -> None:
    st.sidebar.markdown(f"<div class='zyn-side-label'>{escape(text_)}</div>",
                        unsafe_allow_html=True)


def empty(title: str, body: str) -> None:
    """What is missing and the one thing to do about it."""
    st.markdown(f"<div class='zyn-empty'><b>{escape(title)}</b><span>{escape(body)}</span></div>",
                unsafe_allow_html=True)


def run_label(run: dict) -> str:
    """'Sift · icx100_srs.md · 13 Nov 17:57' instead of the raw run ID."""
    rid, wf = run["run_id"], run["workflow"]
    from harness.sift.pipeline import LEGACY_WORKFLOWS

    name = "Sift" if wf in LEGACY_WORKFLOWS else WORKFLOW_NAME.get(
        wf, wf.replace("-", " ").capitalize())
    try:
        when = datetime.strptime(rid[:15], "%Y%m%d-%H%M%S").strftime("%d %b %H:%M")
    except ValueError:
        when = rid
    note = (run.get("note") or "").split(" sha256=")[0]
    note = note if len(note) <= 42 else note[:41] + "…"
    return " · ".join(x for x in (name, note, when) if x)
