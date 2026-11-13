"""Hard rules of the Zyn design system (docs/design-system.md, section 6).

Any screen added under harness/review/ goes through these checks automatically.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from harness.review import ui

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "harness" / "review"
DOC = (ROOT / "docs" / "design-system.md").read_text(encoding="utf-8")
SCREENS = [p for p in REVIEW.glob("*.py") if p.name not in {"ui.py", "__init__.py"}]

COLOUR = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(|hsla?\(|oklch\(")
FONTS = ("Space Grotesk", "Inter", "IBM Plex Mono", "monospace", "sans-serif")
TOKEN_DEF = re.compile(r"(--zyn-[a-z0-9-]+)\s*:")
TOKEN_USE = re.compile(r"var\((--zyn-[a-z0-9-]+)\)")


@pytest.mark.parametrize("screen", SCREENS, ids=lambda p: p.name)
def test_screens_use_components_not_inline_styles(screen):
    code = screen.read_text(encoding="utf-8")
    assert not COLOUR.findall(code), f"{screen.name}: colour value; use a ui tone"
    # An HTML style attribute carries CSS (a colon); a Python style="ears" argument does not.
    assert not re.search(r"style\s*=\s*['\"][^'\"]*:", code), f"{screen.name}: inline style= HTML"
    for call in ("st.title(", "st.header(", "st.subheader("):
        assert call not in code, f"{screen.name}: {call} ; use ui.page_header or ui.section"


@pytest.mark.parametrize("screen", SCREENS, ids=lambda p: p.name)
def test_screens_load_the_design_system_once(screen):
    code = screen.read_text(encoding="utf-8")
    if "st.set_page_config" not in code:
        return
    after = code.split("st.set_page_config", 1)[1]
    assert code.count("ui.inject()") == 1
    # inject is the next statement after the page config
    assert after.split("\n", 2)[1].strip() == "ui.inject()"


def test_literal_values_only_in_token_blocks():
    assert not COLOUR.findall(ui.RULES), "colour value in RULES; add a token"
    for font in FONTS:
        assert font not in ui.RULES, f"font name '{font}' in RULES; use --zyn-font-*"


def test_every_token_used_is_defined_and_documented():
    defined = set(TOKEN_DEF.findall(ui.TOKENS_LIGHT))
    assert set(TOKEN_DEF.findall(ui.TOKENS_DARK)) <= defined, "dark token without a light one"
    used = set(TOKEN_USE.findall(ui.RULES))
    assert not used - defined, f"undefined tokens: {sorted(used - defined)}"
    unused = defined - used
    assert not unused, f"tokens defined but never used: {sorted(unused)}"
    missing = sorted(t for t in defined if f"`{t}`" not in DOC)
    assert not missing, f"tokens not in docs/design-system.md: {missing}"


def test_every_tone_has_a_class_and_bad_tones_fail():
    for tone in ui.TONES:
        assert f".t-{tone} {{" in ui.RULES
        assert f"`{tone}`" in DOC or f"| {tone} |" in DOC
    assert set(ui.STATUS_TONE.values()) <= set(ui.TONES)
    with pytest.raises(ValueError):
        ui.badge("x", "red")


def test_every_component_is_documented():
    public = [n for n, f in vars(ui).items()
              if callable(f) and not n.startswith("_") and f.__module__ == ui.__name__
              and n not in {"inject", "run_label"}]
    missing = [n for n in public if f"ui.{n}" not in DOC]
    assert not missing, f"components not in docs/design-system.md: {missing}"


def test_no_em_dashes_in_user_facing_text():
    for path in [*SCREENS, REVIEW / "ui.py", ROOT / "docs" / "design-system.md"]:
        assert "—" not in path.read_text(encoding="utf-8"), path.name


# ---- web app (web/src): the same rules for the React screen -------------------------------

WEB = ROOT / "web" / "src"
TOKENS_CSS = (WEB / "styles" / "tokens.css").read_text(encoding="utf-8")
WEB_CSS = [p for p in (WEB / "styles").glob("*.css") if p.name != "tokens.css"]
WEB_CODE = [p for p in WEB.rglob("*.ts*") if p.suffix in {".ts", ".tsx"}]
CSS_TOKEN_DEF = re.compile(r"(--zyn-[a-z0-9-]+)\s*:")
DURATION = re.compile(r"\b\d+(?:\.\d+)?m?s\b")


def _strip_css_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)


@pytest.mark.parametrize("path", WEB_CSS, ids=lambda p: p.name)
def test_web_css_uses_tokens_only(path):
    css = _strip_css_comments(path.read_text(encoding="utf-8"))
    assert not COLOUR.findall(css), f"{path.name}: colour value; add a token in tokens.css"
    for font in ("Space Grotesk", "Inter", "IBM Plex Mono", "monospace", "sans-serif"):
        assert font not in css, f"{path.name}: font name '{font}'; use --zyn-font-*"
    assert not DURATION.findall(css), f"{path.name}: literal duration; use --zyn-fast/base/slow/loop"
    assert "transition: all" not in css


@pytest.mark.parametrize("path", WEB_CODE, ids=lambda p: p.name)
def test_web_code_has_no_literal_styling(path):
    code = path.read_text(encoding="utf-8")
    assert not COLOUR.findall(code), f"{path.name}: colour value; use a tone or token"
    assert not re.search(r"fontFamily|fontSize|color:", code), f"{path.name}: inline type/colour"
    if path.name != "motion.ts":
        assert "duration:" not in code, f"{path.name}: animation timing; use motion.ts presets"


def test_web_tokens_are_defined_used_and_documented():
    defined = set(CSS_TOKEN_DEF.findall(TOKENS_CSS))
    # a token may be used by another token (the ramp feeds the roles)
    used_text = TOKENS_CSS + "".join(p.read_text(encoding="utf-8") for p in [*WEB_CSS, *WEB_CODE])
    used = set(re.findall(r"var\((--zyn-[a-z0-9-]+)", used_text))
    assert not used - defined, f"undefined tokens: {sorted(used - defined)}"
    unused = sorted(t for t in defined - used if not t.startswith("--zyn-z-"))
    assert not unused, f"tokens never used: {unused}"
    missing = sorted(t for t in defined if f"`{t}`" not in DOC)
    assert not missing, f"tokens not in docs/design-system.md: {missing}"


def test_web_components_are_documented():
    ui_src = (WEB / "components" / "ui.tsx").read_text(encoding="utf-8")
    names = re.findall(r"export (?:const|function) ([A-Z][a-z][A-Za-z]*)", ui_src)
    names += ["DecisionBar", "Drawer", "Pixels", "Loading", "JobPanel", "Shimmer"]
    missing = [n for n in names if f"`{n}`" not in DOC]
    assert not missing, f"web components not in docs/design-system.md: {missing}"


def test_web_has_no_em_dashes():
    for p in [*WEB_CSS, *WEB_CODE, WEB / "styles" / "tokens.css"]:
        assert "—" not in p.read_text(encoding="utf-8"), p.name
