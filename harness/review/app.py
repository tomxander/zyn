"""Review screen. Launch with: .\\review.ps1  (or: python -m streamlit run harness/review/app.py)

Every approve, reject and edit is written to the append-only audit store under the
reviewer's name. AI reviewer verdicts are advice; only a named human decides. Approving an
item the AI objected to needs a written reason.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

from harness import PROTOTYPE_LABEL
from harness.audit.store import AuditStore
from harness.config import DEFAULT_CONFIG, PROJECT_ROOT, load_config
from harness.models.runner import StructuredOutputFailure
from harness.review import ui
from harness.schemas.common import ReqType
from harness.schemas.sift import Modal, QualityFlag
from harness.sift import check as sift_check
from harness.sift import checks, pipeline
from harness.sift.export import export
from harness.taxonomy import load_taxonomy

load_dotenv(PROJECT_ROOT / ".env")
st.set_page_config(page_title="Zyn review (prototype)", page_icon="◆", layout="wide")
ui.inject()
ui.notice(PROTOTYPE_LABEL)

cfg = load_config(os.environ.get("ZYN_CONFIG") or DEFAULT_CONFIG)
audit = AuditStore(cfg.resolved_db_path())
TAX = load_taxonomy()
STATUSES = list(ui.STATUS_TONE)

# ---- sidebar: reviewer, new run, run picker -----------------------------------------

# Name and run are mirrored into the page address so a reload keeps them.
if "reviewer" not in st.session_state:
    st.session_state["reviewer"] = st.query_params.get("reviewer", "")
if "pick_run" not in st.session_state and st.query_params.get("run"):
    st.session_state["pick_run"] = st.query_params["run"]
ui.brand()
ui.side_label("Reviewer")
reviewer = st.sidebar.text_input("Reviewer name (required to decide)", key="reviewer",
                                 placeholder="Your name", label_visibility="collapsed").strip()
if reviewer:
    st.query_params["reviewer"] = reviewer
else:
    st.query_params.pop("reviewer", None)
    st.sidebar.caption("Required to approve, reject, edit or run a stage.")

runs = audit.list_runs()
run_by_id = {r["run_id"]: r for r in runs}
if runs:
    ui.side_label("Run")
    ids = list(run_by_id)
    default = (ids.index(st.session_state["pick_run"])
               if st.session_state.get("pick_run") in ids else 0)
    run_id = st.sidebar.selectbox("Run", ids, index=default, label_visibility="collapsed",
                                  format_func=lambda i: ui.run_label(run_by_id[i]))
    st.session_state["pick_run"] = run_id
    st.query_params["run"] = run_id
    st.sidebar.caption(f"`{run_id}`")

ui.side_label("Start new")
with st.sidebar.expander("Sift run: extract from a spec"):
    up = st.file_uploader("Specification (PDF, DOCX, Markdown, text)",
                          type=["pdf", "docx", "md", "txt"], key="upload")
    if st.button("Ingest and map sections", key="start", disabled=not (up and reviewer)):
        dest = PROJECT_ROOT / "runs" / "uploads" / up.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(up.getvalue())
        with st.spinner("Reading the document and mapping sections..."):
            try:
                rep = pipeline.start(cfg, audit, dest)
                st.session_state["pick_run"] = rep.run_id
                st.rerun()
            except (StructuredOutputFailure, ValueError) as e:
                st.error(str(e))

with st.sidebar.expander("Sift Review: check a requirement set"):
    up_set = st.file_uploader("Requirement set (ReqIF, Excel, CSV)",
                              type=["reqif", "xlsx", "csv"], key="upload_set")
    ears = st.checkbox("Also check EARS sentence patterns", key="ears")
    if st.button("Import and run code checks", key="start_check",
                 disabled=not (up_set and reviewer)):
        dest = PROJECT_ROOT / "runs" / "uploads" / up_set.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(up_set.getvalue())
        try:
            rep = sift_check.start(cfg, audit, dest, style="ears" if ears else None)
            st.session_state["pick_run"] = rep.run_id
            st.rerun()
        except ValueError as e:
            st.error(str(e))

with st.sidebar.expander("Sift Delta: what changed"):
    from harness.sift import delta as sift_delta

    mode = st.radio("Compare", ["New revision of an extracted spec", "Two requirement sets"],
                    key="delta_mode")
    if mode.startswith("New revision"):
        sift_runs = [r["run_id"] for r in audit.list_runs()
                     if r["workflow"] in {pipeline.WORKFLOW, *pipeline.LEGACY_WORKFLOWS}]
        base = st.selectbox("Approved Sift run", sift_runs, key="delta_base")
        up_new = st.file_uploader("New revision (PDF, DOCX, Markdown, text)",
                                  type=["pdf", "docx", "md", "txt"], key="delta_new")
        go = st.button("Compare", key="delta_go", disabled=not (reviewer and base and up_new))
    else:
        up_old = st.file_uploader("Old set (ReqIF, Excel, CSV)", type=["reqif", "xlsx", "csv"],
                                  key="delta_old")
        up_new = st.file_uploader("New set (ReqIF, Excel, CSV)", type=["reqif", "xlsx", "csv"],
                                  key="delta_new_set")
        go = st.button("Compare", key="delta_go_set",
                       disabled=not (reviewer and up_old and up_new))
    if go:
        folder = PROJECT_ROOT / "runs" / "uploads"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / up_new.name).write_bytes(up_new.getvalue())
        try:
            if mode.startswith("New revision"):
                rep = sift_delta.spec_delta(cfg, audit, base, folder / up_new.name)
            else:
                (folder / up_old.name).write_bytes(up_old.getvalue())
                rep = sift_delta.set_delta(cfg, audit, folder / up_old.name,
                                           folder / up_new.name)
            st.session_state["pick_run"] = rep.run_id
            st.rerun()
        except ValueError as e:
            st.error(str(e))

with st.sidebar.expander("Anvil run: test cases"):
    from harness.anvil import pipeline as forge

    sift_runs_f = [r["run_id"] for r in audit.list_runs()
                   if r["workflow"] in {pipeline.WORKFLOW, *pipeline.LEGACY_WORKFLOWS}]
    f_base = st.selectbox("Approved Sift run", sift_runs_f, key="forge_base")
    f_dbc = st.file_uploader("CAN database (DBC); leave empty for the synthetic ICX-100 one",
                             type=["dbc"], key="forge_dbc")
    if st.button("Propose test specs", key="forge_go", disabled=not (reviewer and f_base),
                 help="One model call per section. Code then checks every proposal."):
        dbc_path = PROJECT_ROOT / "data" / "synthetic" / "icx100.dbc"
        if f_dbc:
            dbc_path = PROJECT_ROOT / "runs" / "uploads" / f_dbc.name
            dbc_path.parent.mkdir(parents=True, exist_ok=True)
            dbc_path.write_bytes(f_dbc.getvalue())
        with st.spinner("Proposing a test template for each approved requirement..."):
            try:
                rep = forge.start(cfg, audit, f_base, dbc_path)
                st.session_state["pick_run"] = rep.run_id
                st.rerun()
            except (StructuredOutputFailure, ValueError) as e:
                st.error(str(e))

st.sidebar.caption(f"Generator `{cfg.roles['generator']}` · AI reviewer "
                   f"`{cfg.roles['reviewer']}`")

if not runs:
    ui.empty("No runs yet", "Start one from 'Sift run: extract from a spec' in the sidebar.")
    st.stop()
workflow = run_by_id[run_id]["workflow"]
run_events = audit.events(run_id=run_id)


# ---- shared item card ---------------------------------------------------------------


def doc_order(item: dict) -> tuple:
    """Sort by section number (3 < 10, 7.2 < 7.10), then by ID number within a section."""
    p = item["payload"]
    num = p.get("section_number", p.get("number")) or ""
    parts = tuple(int(x) for x in num.split(".") if x.isdigit()) if num else (-1,)
    tail = item["item_id"].split("@")[0].rsplit("-", 1)[-1]
    return parts, int(tail) if tail.isdigit() else 0


status_badge = ui.status_badge


LABELS_REASON = "Text is correct as written; the objection is only about type, flags or ASIL hint"
REASONS = [
    LABELS_REASON,
    "Text is faithful to the source; the source wording is binding as written",
    "Checked the AI's point against the source and disagree",
]
OTHER = "Other (type a reason)"


def decision_buttons(iid: str, cols, scope: str | None = None,
                     block_approve: str | None = None) -> None:
    status = audit.status(iid)
    if block_approve and status != "approved":
        cols[0].button("Approve", key=f"a-{iid}", disabled=True, help=block_approve,
                       type="primary", use_container_width=True)
        if cols[1].button("Reject", key=f"r-{iid}", use_container_width=True,
                          disabled=not reviewer or status == "rejected"):
            audit.decide(iid, "rejected", reviewer)
            st.rerun()
        return
    needs_reason = status != "approved" and audit.needs_override_reason(iid)
    reason = ""
    if needs_reason:
        # A typed reason for every approval made rejecting the easy path, even for correct
        # requirements. Standard reasons keep the record without the typing; none is
        # preselected, so approving still takes a deliberate choice.
        options = REASONS if scope != "text" else REASONS[1:]
        item = audit.get_item(iid)
        prior = (pipeline.earlier_override(audit, item)
                 if item and item["item_type"] == "requirement" else None)
        if prior and prior.get("reason"):
            earlier = f"As before (run {prior['run_id']}): {prior['reason']}"
            options = [earlier, *[o for o in options if o != prior["reason"]]]
            st.caption(f"{prior['by']} approved the same wording over an AI objection in run "
                       f"{prior['run_id']}. That reason is offered first.")
        pick = st.selectbox("The AI reviewer objected. Reason for approving anyway:",
                            [*options, OTHER], index=None, placeholder="Choose a reason",
                            key=f"o-{iid}")
        reason = (st.text_input("Reason", key=f"ot-{iid}") if pick == OTHER else pick) or ""
    if cols[0].button("Approve", key=f"a-{iid}", type="primary", use_container_width=True,
                      disabled=not reviewer or status == "approved"
                      or (needs_reason and not reason.strip())):
        audit.decide(iid, "approved", reviewer, comment=reason or None)
        st.rerun()
    if cols[1].button("Reject", key=f"r-{iid}", use_container_width=True,
                      disabled=not reviewer or status == "rejected"):
        audit.decide(iid, "rejected", reviewer)
        st.rerun()


def section_text(item: dict) -> str:
    sec = audit.get_item(f"{item['run_id']}:{item['payload'].get('section_id')}")
    return sec["payload"]["text"] if sec else item["payload"].get("source_quote", "")


def support_states(item: dict, review: dict | None) -> list[tuple[str, bool]]:
    """Concrete checks, each passed or not. Shown instead of any model confidence."""
    p = item["payload"]
    states = []
    if "grounded" in p:
        states.append(("Quote located in source" if p["grounded"] else "Quote NOT in source",
                       bool(p["grounded"])))
    if p.get("source_quote"):
        changed = checks.modal_changed(p["source_quote"], p.get("text", ""))
        states.append(("Modal verb kept" if not changed else "Modal verb changed", not changed))
        added = checks.new_numbers(p.get("text", ""), section_text(item))
        if not p.get("clarification"):
            states.append(("Values from source only" if not added
                           else "Adds values: " + ", ".join(added), not added))
    if p.get("weak_words_found") is not None:
        ok = not p.get("weak_word_unflagged")
        states.append(("Vague words flagged" if ok else "Vague words unflagged", ok))
    tbd = pipeline.open_placeholders(p)
    if tbd:
        states.append((f"{len(tbd)} placeholder(s) open", False))
    if review and review.get("detail"):
        v = review["detail"]["verdict"]
        states.append(("AI reviewer accepted" if v == "accept" else f"AI reviewer: {v}",
                       v == "accept"))
    return states


def needs_attention(item: dict) -> bool:
    return not all(ok for _, ok in support_states(item, audit.latest_ai_review(item["item_id"])))


def requirement_card(item: dict) -> None:
    iid, p = item["item_id"], item["payload"]
    review = audit.latest_ai_review(iid)
    d = review["detail"] if review else None
    with st.container(border=True):
        sec = f"§{p['section_number']}" if p.get("section_number") else ""
        ui.card_head(pipeline.display_id(iid),
                     [f"v{item['version']}", sec, p.get("subsystem_id"), p.get("req_type"),
                      p.get("modal"), p.get("verification_method")],
                     status_badge(item["status"]))
        ui.text(p.get("text", ""))
        where = " · ".join(x for x in (
            f"page {p['page']}" if p.get("page") else "",
            f"characters {p['quote_offset'][0]}-{p['quote_offset'][1]} of the section"
            if p.get("quote_offset") else "") if x)
        ui.quote("Source: “" + ui.escape(p.get("source_quote", "")) + "”"
                 + (" " + ui.quiet(f"({where})") if where else ""))
        if item["version"] > 1:
            from harness.sift.delta import word_diff
            first = audit.get_item(iid, version=1)["payload"].get("text", "")
            if first != p.get("text", ""):
                ops = word_diff(first, p.get("text", ""))
                st.markdown(ui.quiet("Changed from the extracted version:") + " "
                            + ui.diff_html(ops), unsafe_allow_html=True)
        chips = support_states(item, review)
        if chips:
            st.markdown(ui.chips(chips), unsafe_allow_html=True)
        flags = p.get("quality_flags") or []
        extra = f" · ASIL hint (model suggestion): {p['asil_hint']}" if p.get("asil_hint") else ""
        st.caption(("Quality flags: " + ", ".join(flags) if flags else "Quality flags: none")
                   + extra)
        if p.get("grounded") is False:
            st.error("Ungrounded: the quote was not found in the source section (code check).")
        if p.get("modal_changed"):
            st.error("Modal verb changed from the source (code check).")
        if p.get("weak_word_unflagged"):
            st.warning("Weak words in the source not flagged by the model: "
                       + ", ".join(p.get("weak_words_found", [])) + " (code check).")
        if d:
            msg = f"AI reviewer ({review['actor']}, on v{review['object_version']}): **{d['verdict']}**"
            if d.get("objection_scope") == "labels":
                msg += " · about labels only, the text is fine"
            elif d.get("objection_scope") == "text":
                msg += " · about the requirement text"
            if d.get("issues"):
                msg += "  \n" + "  \n".join(f"- {x}" for x in d["issues"])
            if d.get("suggested_text"):
                msg += f"  \nSuggested text: {d['suggested_text']}"
            if d.get("suggested_req_type"):
                msg += f"  \nSuggested type: {d['suggested_req_type']}"
            if d.get("suggested_flags") is not None:
                msg += "  \nSuggested flags: " + (", ".join(d["suggested_flags"]) or "none")
            (st.success if d["verdict"] == "accept" else st.warning)(msg)

        clar = pipeline.latest_clarification(audit, iid) if flags else None
        if clar:
            c = clar["detail"]
            msg = (f"Proposed clarification ({clar['actor']}, advice for you and the spec "
                   f"author): **{c['proposed_text']}**  \nResolves: "
                   + (", ".join(c["resolves"]) or "none") + f"  \n{c['rationale']}")
            if c["open_questions"]:
                msg += "  \nQuestions for the spec author:  \n" + "  \n".join(
                    f"- {q}" for q in c["open_questions"])
            st.info(msg)
            if c["problems"]:
                st.error("Clarification cannot be used with one click (code check): "
                         + "; ".join(c["problems"]) + ". Use Edit if part of it is right.")
        tbd = pipeline.open_placeholders(p)
        if tbd:
            st.warning(f"{len(tbd)} placeholder(s) still open: " + ", ".join(tbd)
                       + ". Fill them with Edit once the spec author answers, or approve "
                         "with them as open items.")
        if p.get("clarification") and p["clarification"].get("open_questions"):
            st.caption("Open questions carried into export: "
                       + "; ".join(p["clarification"]["open_questions"]))

        b = st.columns([1, 1, 1.6, 3])
        decision_buttons(iid, b, scope=(d or {}).get("objection_scope"))
        new = {**p}
        if d and d.get("suggested_text"):
            new["text"] = d["suggested_text"]
        if d and d.get("suggested_req_type"):
            new["req_type"] = d["suggested_req_type"]
        if d and d.get("suggested_flags") is not None:
            new["quality_flags"] = d["suggested_flags"]
        problems = (checks.suggestion_problems(d["suggested_text"], p.get("source_quote", ""),
                                               section_text(item))
                    if d and d.get("suggested_text") and new["text"] != p.get("text") else [])
        # Only offer the fix when it changes something and passes the code check; an unchanged
        # "fix" would otherwise clear the override-reason rule without addressing anything.
        changes = any(new.get(k) != p.get(k) for k in ("text", "req_type", "quality_flags"))
        can_apply = bool(d) and d["verdict"] == "revise" and changes and not problems
        if item["version"] > 1 and p.get("clarification"):
            # Clarified wording departs from the source on purpose and reviewers fill
            # placeholders with new values, so only the modal verb is held to the source.
            own = ([f"changes the modal verb from '{checks.modal_of(p['source_quote'])}'"]
                   if checks.modal_changed(p.get("source_quote", ""), p.get("text", ""))
                   else [])
        elif item["version"] > 1:
            own = checks.suggestion_problems(p.get("text", ""), p.get("source_quote", ""),
                                             section_text(item))
        else:
            own = []
        if own:
            st.error("This version's text fails the code check: " + "; ".join(own)
                     + ". Revert to original or edit it.")
        if problems:
            st.error("AI suggestion cannot be applied with one click (code check): "
                     + "; ".join(problems) + ". Use Edit if part of it is right.")
        if can_apply and b[2].button("Apply AI suggestion", key=f"s-{iid}", disabled=not reviewer):
            audit.edit_item(iid, new, reviewer, comment="applied AI reviewer suggestion",
                            source="ai_suggestion")
            st.rerun()
        if (clar and not clar["detail"]["problems"]
                and b[2].button("Use clarification", key=f"c-{iid}", disabled=not reviewer)):
            pipeline.apply_clarification(audit, iid, reviewer)
            st.rerun()
        if item["version"] > 1 and b[2].button("Revert to original", key=f"v-{iid}",
                                               disabled=not reviewer):
            original = audit.get_item(iid, version=1)["payload"]
            audit.edit_item(iid, original, reviewer, comment="reverted to the extracted version")
            st.rerun()
        with b[3].expander("Edit"):
            new_text = st.text_area("Requirement text", p.get("text", ""), key=f"t-{iid}")
            types = [t.value for t in ReqType]
            new_type = st.selectbox("Type", types, index=types.index(p.get("req_type", "other")),
                                    key=f"ty-{iid}")
            modals = [m.value for m in Modal]
            new_modal = st.selectbox("Modal", modals,
                                     index=modals.index(p["modal"]) if p.get("modal") in modals
                                     else 0, key=f"mo-{iid}") if "modal" in p else None
            new_flags = st.multiselect("Quality flags", [f.value for f in QualityFlag],
                                       default=flags, key=f"fl-{iid}")
            note = st.text_input("Reason for edit", key=f"n-{iid}")
            if st.button("Save edit as new version", key=f"e-{iid}", disabled=not reviewer):
                new = {**p, "text": new_text, "req_type": new_type, "quality_flags": new_flags}
                if new_modal:
                    new["modal"] = new_modal
                audit.edit_item(iid, new, reviewer, comment=note or None)
                st.rerun()


def mapping_card(item: dict) -> None:
    iid, p = item["item_id"], item["payload"]
    with st.container(border=True):
        ui.card_head(f"§{p.get('number') or '-'}",
                     [f"→ {p['subsystem_id']}", f"model self-rating {p['confidence']:.2f}"],
                     status_badge(item["status"]),
                     extra=f"<b>{ui.escape(p['heading'])}</b>")
        st.caption(p["rationale"])
        with st.expander("Section text (preview)"):
            st.text(p.get("text_preview", ""))
        b = st.columns([1, 1, 4])
        decision_buttons(iid, b)
        with b[2].expander("Change subsystem"):
            ids_ = TAX.ids()
            new = st.selectbox("Subsystem", ids_, index=ids_.index(p["subsystem_id"]),
                               format_func=lambda i: f"{i}: {next(s.name for s in TAX.subsystems if s.id == i)}",
                               key=f"sub-{iid}")
            if st.button("Save", key=f"es-{iid}", disabled=not reviewer):
                audit.edit_item(iid, {**p, "subsystem_id": new}, reviewer,
                                comment=f"subsystem {p['subsystem_id']} -> {new}")
                st.rerun()


def counts_row(items: list[dict]) -> None:
    cols = st.columns(4)
    for col, s in zip(cols, ("proposed", "edited", "approved", "rejected"), strict=True):
        col.metric(s.capitalize(), sum(1 for i in items if i["status"] == s))


def metrics_panel() -> None:
    from harness.metrics import run_metrics

    m = run_metrics(audit, run_id, cfg)
    mc = m["model"]
    ui.section("Effort and cost", "From the audit log. Elapsed times include idle time.")
    c = st.columns(4)
    c[0].metric("Model calls", mc["calls"], help=f"{mc['schema_retries']} schema retries, "
                f"{mc['failed_calls']} failed, {mc['blocked_offline']} blocked offline")
    c[1].metric("Tokens in / out", f"{mc['tokens_in']:,} / {mc['tokens_out']:,}")
    c[2].metric("Model cost (USD)", f"{mc['cost_usd']:.2f}" + ("" if mc["cost_complete"]
                                                                 else " +?"),
                help="Prices per profile in config.yaml. '+?' means a profile has no price.")
    c[3].metric("Model time (s)", mc["model_seconds"])
    for kind, r in m["review"].items():
        st.caption(f"{kind.replace('_', ' ')}: {r['decided']} of {r['items']} decided · "
                   f"{r['edited_items']} edited · median "
                   f"{r['median_minutes_to_first_decision'] or '-'} min from output to first "
                   "decision" + (f" · {r['carried_over']} carried over"
                                 if r.get("carried_over") else ""))
    ag = m["agreement"]
    if "ai_reviewer_on_requirements" in ag:
        a = ag["ai_reviewer_on_requirements"]
        st.caption(f"AI reviewer vs people: objections upheld {a['objection_upheld']}, "
                   f"overruled {a['objection_overruled']} · accepts confirmed "
                   f"{a['accept_confirmed']}, overruled {a['accept_overruled']} · "
                   f"undecided {a['undecided']}")
    for src, t in ag.get("findings_by_source", {}).items():
        st.caption(f"Findings by {src}: {t['confirmed']} confirmed, {t['dismissed']} "
                   f"dismissed, {t['open']} open")
    st.divider()


def audit_tab() -> None:
    metrics_panel()
    st.dataframe(
        [{k: e[k] for k in ("event_id", "ts", "actor", "action", "object_id", "object_version",
                            "model_served", "tokens_in", "tokens_out", "latency_ms", "attempt")}
         for e in run_events], use_container_width=True)
    st.download_button("Download audit log (JSON)", json.dumps(run_events, indent=2),
                       file_name=f"audit-{run_id}.json")


if not reviewer:
    st.info("Read-only until you enter your name under Reviewer in the sidebar.", icon="👤")

# ---- Sift Review runs: findings on an existing requirement set --------------------------

FINDING_STATE = {"proposed": ("Open", "warn"), "approved": ("Confirmed", "ok"),
                 "rejected": ("Dismissed", "muted"), "edited": ("Open", "warn")}
DISMISS_REASONS = ["Not a problem in this context", "Defined elsewhere in the project",
                   "Known and accepted", "Duplicate of another finding"]


def highlight(text: str, evidence: str) -> str:
    from html import escape
    t, e = escape(text), escape(evidence or "")
    i = t.lower().find(e.lower()) if e else -1
    if i < 0:
        return t
    return t[:i] + f"<mark>{t[i:i + len(e)]}</mark>" + t[i + len(e):]


def finding_card(item: dict, stab: dict | None = None) -> None:
    iid, p = item["item_id"], item["payload"]
    label, colour = FINDING_STATE[item["status"]]
    who = "code check" if p["source"] == "code" else f"AI reviewer ({item['created_by']})"
    with st.container(border=True):
        ui.card_head(p["req_id"], [p["category"], f"found by {who}"],
                     ui.badge(label, colour))
        ui.text_html(highlight(p["requirement_text"], p["evidence"]))
        if stab and iid in stab and stab[iid][1] > 1:
            k, n = stab[iid]
            st.markdown(ui.chip(f"Seen in {k} of {n} AI passes", "ok" if k == n else "warn"),
                        unsafe_allow_html=True)
        if p["evidence_found"]:
            st.caption(f"Quoted words located in the requirement: \"{p['evidence']}\"")
        else:
            st.error(f"The quoted words \"{p['evidence']}\" are not in the requirement text "
                     "(code check). Treat this finding with caution.")
        st.write(p["explanation"])
        also = sift_check.corroborations(audit, iid)
        if also:
            st.caption("Also reported by: " + ", ".join(sorted(
                {"code check" if c["source"] == "code" else "AI reviewer" for c in also})))
        st.caption(f"Question for the author: {p['question_for_author']}"
                   + (f" · Related: {', '.join(p['related_ids'])}" if p.get("related_ids")
                      else ""))
        prior = p.get("prior")
        if prior:
            st.info(f"Same finding on the same text was {prior['decision'].replace('approved', 'confirmed').replace('rejected', 'dismissed')} "
                    f"by {prior['by']} in run {prior['run_id']}"
                    + (f": {prior['comment']}" if prior.get("comment") else "."))
        b = st.columns([1, 1, 3])
        if b[0].button("Confirm", key=f"a-{iid}", type="primary", use_container_width=True,
                       disabled=not reviewer or item["status"] == "approved"):
            audit.decide(iid, "approved", reviewer)
            st.rerun()
        reason = b[2].selectbox("Dismissal reason (optional)", DISMISS_REASONS, index=None,
                                placeholder="Reason, if dismissing", key=f"dr-{iid}",
                                label_visibility="collapsed")
        if b[1].button("Dismiss", key=f"r-{iid}", use_container_width=True,
                       disabled=not reviewer or item["status"] == "rejected"):
            audit.decide(iid, "rejected", reviewer, comment=reason)
            st.rerun()


if workflow == sift_check.WORKFLOW:
    meta = audit.get_item(f"SET-{run_id}")["payload"]
    ui.page_header("Sift Review", meta["filename"],
                   f"{meta['count']} requirements · {meta['source_format']} · columns used: "
                   + ", ".join(f"{k} = {v}" for k, v in meta["columns_used"].items())
                   + f" · sha256 {meta['sha256'][:16]}…")
    reqs_in = sorted(audit.list_items(run_id, "imported_requirement"),
                     key=lambda i: i["payload"]["order"])
    order = {r["payload"]["ext_id"]: r["payload"]["order"] for r in reqs_in}
    finds = sorted(audit.list_items(run_id, "finding"),
                   key=lambda f: (order.get(f["payload"]["req_id"], 10**9), f["item_id"]))
    open_n = sum(1 for f in finds if f["status"] in ("proposed", "edited"))
    tf, tr, te, ta = st.tabs([f"Findings ({open_n} open of {len(finds)})",
                              f"Requirements ({len(reqs_in)})", "Export and score",
                              "Audit log"])
    with tf:
        all_b = sift_check.batches(audit, run_id)
        all_w = sift_check.conflict_windows(audit, run_id)
        left_b = len(all_b) - len(sift_check.ai_done(audit, run_id))
        left_w = len(all_w) - len(sift_check.conflicts_done(audit, run_id))
        left = left_b + left_w
        if left and not reviewer:
            st.warning("Enter your name in the sidebar to run the AI review.")
        if st.button(f"Run AI review ({left_b} of {len(all_b)} batches and {left_w} of "
                     f"{len(all_w)} set-wide conflict passes left)", key="ai_check",
                     disabled=not (reviewer and left),
                     help="Each batch checks up to 15 requirements on their own; the "
                          "conflict pass reads the whole set for contradictions."):
            with st.spinner("AI reviewer reading the set, batch by batch..."):
                rep = sift_check.ai_review(cfg, audit, run_id)
            audit.log_event(reviewer, "stage_started", run_id=run_id,
                            detail={"stage": "ai_review", **rep.as_dict()})
            if rep.failed:
                st.error("Failed batches: " + json.dumps(rep.failed))
            st.rerun()
        done_passes = sift_check.passes_done(audit, run_id)
        if 1 in done_passes:
            want = st.number_input("AI passes in total", 2, 5, max(3, len(done_passes)),
                                   key="npass", help="Each extra pass repeats the whole AI "
                                   "review and costs about the same as the first.")
            if len(done_passes) < want and st.button(
                    f"Stability check: run {int(want) - len(done_passes)} more AI passes",
                    key="stab", disabled=not reviewer,
                    help="Shows which AI findings recur when the same review is repeated. "
                         "A finding seen once is weaker evidence than one seen every time."):
                with st.spinner("Repeating the AI review..."):
                    rep = sift_check.stability_check(cfg, audit, run_id, int(want))
                audit.log_event(reviewer, "stage_started", run_id=run_id,
                                detail={"stage": "stability", **rep.as_dict()})
                if rep.failed:
                    st.error("A pass failed and was not recorded: " + json.dumps(rep.failed))
                st.rerun()
        carry = sift_check.carry_over_candidates(audit, run_id)
        if carry and st.button(f"Apply {len(carry)} earlier decisions on identical findings",
                               key="carry", disabled=not reviewer,
                               help="Findings on unchanged text that a person already "
                                    "confirmed or dismissed in an earlier run."):
            sift_check.apply_prior(audit, run_id, reviewer)
            st.rerun()
        cols = st.columns(4)
        cols[0].metric("Open", open_n)
        cols[1].metric("Confirmed", sum(1 for f in finds if f["status"] == "approved"))
        cols[2].metric("Dismissed", sum(1 for f in finds if f["status"] == "rejected"))
        cols[3].metric("Requirements with findings", len({f["payload"]["req_id"]
                                                          for f in finds}))
        g1, g2, g3 = st.columns(3)
        cats = sorted({f["payload"]["category"] for f in finds})
        pick_cat = g1.multiselect("Finding", cats, default=cats, key="fcat")
        pick_src = g2.multiselect("Found by", ["code", "ai"], default=["code", "ai"],
                                  key="fsrc")
        states = ["Open", "Confirmed", "Dismissed"]
        pick_st = g3.multiselect("Status", states, default=states, key="fst")
        stab = sift_check.stability(audit, run_id)
        multi = len(done_passes) > 1
        only_stable = multi and st.toggle("Only AI findings seen in every pass (code findings "
                                          "always shown)", key="fstable")
        for f in finds:
            p = f["payload"]
            if (p["category"] in pick_cat and p["source"] in pick_src
                    and FINDING_STATE[f["status"]][0] in pick_st
                    and not (only_stable and f["item_id"] in stab
                             and stab[f["item_id"]][0] < stab[f["item_id"]][1])):
                finding_card(f, stab)
    with tr:
        per = {}
        for f in finds:
            per.setdefault(f["payload"]["req_id"], []).append(f)
        st.dataframe([{
            "ID": r["payload"]["ext_id"], "Heading": r["payload"]["heading"],
            "Requirement": r["payload"]["text"],
            "Findings": ", ".join(sorted({f["payload"]["category"]
                                          for f in per.get(r["payload"]["ext_id"], [])})),
            "Open": sum(1 for f in per.get(r["payload"]["ext_id"], [])
                        if f["status"] in ("proposed", "edited")),
        } for r in reqs_in], use_container_width=True, hide_index=True)
    with te:
        st.write("Exports every finding with its status. Open findings are marked unreviewed.")
        if st.button("Export findings (JSON, Excel)", key="export_f",
                     disabled=not (reviewer and finds)):
            st.session_state["last_export_f"] = sift_check.export_findings(audit, run_id,
                                                                           reviewer)
        res = st.session_state.get("last_export_f")
        if res:
            st.success(f"Exported {res['count']} findings.")
            for kind, path in res["files"].items():
                st.download_button(f"Download {kind.upper()}", Path(path).read_bytes(),
                                   file_name=Path(path).name, key=f"dlf-{kind}")
        st.divider()
        key_default = (PROJECT_ROOT / "data" / "synthetic" / "icx100_answer_key.json"
                       if meta["filename"].startswith("icx100") else "")
        key_path = st.text_input("Answer key (JSON with gold_id and flags)",
                                 str(key_default), key="keypath")
        if key_path and Path(key_path).exists() and st.button("Score against answer key",
                                                               key="score"):
            rows_ = [("Code checks only", ("code",), 1), ("AI reviewer only", ("ai",), 1),
                     ("Code and AI together", ("code", "ai"), 1)]
            n_pass = len(sift_check.passes_done(audit, run_id))
            if n_pass > 1:
                rows_.append((f"Code and AI, AI findings seen in all {n_pass} passes",
                              ("code", "ai"), n_pass))
            for label_, srcs, mp in rows_:
                s = sift_check.score(audit, run_id, key_path, srcs, min_passes=mp)
                st.markdown(f"**{label_}:** {s['found']} of {s['required_flags']} expected "
                            f"flags found · {s['flags_not_in_key']} flags not in the key · "
                            f"{s['requirements_with_findings']} of {s['requirements']} "
                            "requirements with findings")
                if s["missed"]:
                    st.caption("Missed: " + ", ".join(s["missed"]))
            st.caption("Scores count findings before human review. The answer key is "
                       "author-made and AI-reviewed, not engineer-reviewed.")
    with ta:
        audit_tab()
    st.stop()


# ---- Anvil runs: test specs, generated cases, fault checks ------------------------------

SPEC_FIELDS = ["input_signal", "initial_value", "input_value", "threshold", "direction",
               "output_signal", "expected_value", "max_latency_ms", "hold_ms", "message",
               "timeout_ms", "period_ms"]


TRACK_FIELDS = ["track_low_factor", "track_low_offset", "track_high_factor",
                "track_high_offset"]


def spec_card(item: dict, db) -> None:
    from harness.anvil import pipeline as forge
    from harness.schemas.forge import Template

    iid, p = item["item_id"], item["payload"]
    with st.container(border=True):
        ui.card_head(p["req_id"], [f"template {p['template']}",
                                   f"v{item['version']}"], status_badge(item["status"]))
        ui.text(p["requirement_text"])
        params = {k: p[k] for k in SPEC_FIELDS + TRACK_FIELDS if p.get(k) not in (None, "")}
        if params:
            st.markdown(" · ".join(f"`{k}` = **{v:g}**" if isinstance(v, float) else
                                   f"`{k}` = **{v}**" for k, v in params.items()))
        for src in p.get("value_sources", []):
            st.caption(f"{src['param']} from: \"{src['quote']}\"")
        from harness.anvil import impact as fimpact
        rstate = fimpact.spec_requirement_state(audit, p)
        if rstate != "current":
            now = fimpact.requirement_now(audit, p)
            st.warning({
                "changed": "The requirement has a newer approved version: "
                           f"\"{now['text']}\". Propose this spec again.",
                "pending": "The requirement has an update awaiting approval: "
                           f"\"{now['text']}\".",
                "dropped": "The requirement is no longer approved (rejected). Reject this "
                           "spec; its cases are stale.",
            }[rstate])
        if p.get("manual_test_idea"):
            st.info(f"Manual test idea: {p['manual_test_idea']}")
        for a in p.get("assumptions", []):
            st.caption(f"Assumption: {a}")
        if p.get("missing"):
            st.warning("Not given by the requirement: " + "; ".join(p["missing"]))
        if p["problems"]:
            st.error("Code checks failed: " + "; ".join(p["problems"])
                     + ". Edit the spec or reject it; cases are only generated from specs "
                       "that pass.")
        else:
            st.caption("✓ Code checks passed: template complete, signals in the DBC, values in "
                       "range and traced to the requirement text.")
        b = st.columns([1, 1, 4])
        decision_buttons(iid, b, block_approve=(
            "Fails the code checks: edit the spec until they pass, or reject it."
            if p["problems"] else None))
        with b[2].expander("Edit spec"):
            new = dict(p)
            tmpl = [t.value for t in Template]
            new["template"] = st.selectbox("Template", tmpl, index=tmpl.index(p["template"]),
                                           key=f"ft-{iid}")
            ins = [""] + sorted(n for n, s in db.signals.items() if s.cluster_receives)
            outs = [""] + sorted(n for n, s in db.signals.items() if not s.cluster_receives)
            msgs = [""] + sorted(db.messages)
            c1, c2, c3 = st.columns(3)
            new["input_signal"] = c1.selectbox(
                "Input signal", ins, index=ins.index(p["input_signal"])
                if p.get("input_signal") in ins else 0, key=f"fi-{iid}") or None
            new["output_signal"] = c2.selectbox(
                "Output signal", outs, index=outs.index(p["output_signal"])
                if p.get("output_signal") in outs else 0, key=f"fo-{iid}") or None
            new["message"] = c3.selectbox(
                "Message", msgs, index=msgs.index(p["message"])
                if p.get("message") in msgs else 0, key=f"fm-{iid}") or None
            dirs = ["", "below", "above"]
            new["direction"] = c1.selectbox("Direction", dirs,
                                            index=dirs.index(p.get("direction") or ""),
                                            key=f"fd-{iid}") or None
            nums = ["initial_value", "input_value", "threshold", "expected_value",
                    "max_latency_ms", "hold_ms", "timeout_ms", "period_ms", *TRACK_FIELDS]
            cols = st.columns(4)
            for n, k in enumerate(nums):
                v = cols[n % 4].text_input(k, "" if p.get(k) is None else f"{p[k]:g}",
                                           key=f"fn-{k}-{iid}")
                try:
                    new[k] = float(v) if v.strip() else None
                except ValueError:
                    new[k] = p.get(k)
            new["manual_test_idea"] = st.text_area(
                "Manual test idea (for not_automatable)", p.get("manual_test_idea") or "",
                key=f"fmi-{iid}") or None
            note = st.text_input("Reason for edit", key=f"fr-{iid}")
            if st.button("Save as new version", key=f"fe-{iid}", disabled=not reviewer):
                new["problems"] = forge.revalidate(audit, run_id, new)
                audit.edit_item(iid, new, reviewer, comment=note or None)
                st.rerun()


if workflow == "forge":
    from harness.anvil import pipeline as forge
    from harness.anvil.dbc import load_dbc

    meta = audit.get_item(f"FORGE-{run_id}")["payload"]
    db = load_dbc(meta["dbc_path"])
    ui.page_header("Anvil", f"Test cases from Sift run {meta['sift_run']}",
                   f"{meta['requirements']} approved requirements · CAN database "
                   f"{meta['dbc_file']} (sha256 {meta['dbc_sha256'][:16]}…) · the model "
                   "proposes a template per requirement; code checks it, generates the cases "
                   "and tests them against injected faults")
    specs = audit.list_items(run_id, "test_spec")
    cases = audit.list_items(run_id, "test_case")
    faults = forge.fault_results(audit, run_id)
    t1, t2, t3, t4 = st.tabs([f"1. Test specs ({len(specs)})", f"2. Cases ({len(cases)})",
                              "3. Export", "Audit log"])
    with t1:
        counts_row(specs)
        templates = sorted({s["payload"]["template"] for s in specs})
        g1, g2 = st.columns(2)
        pick_t = g1.multiselect("Template", templates, default=templates, key="ftmpl")
        only_bad = g2.toggle("Only specs failing code checks", key="fbad")
        missing_specs = forge.without_spec(audit, run_id)
        if missing_specs:
            st.warning(f"{len(missing_specs)} approved requirements have no spec (a model call "
                       "failed): " + ", ".join(pipeline.display_id(r["item_id"])
                                               for r in missing_specs))
            if st.button("Retry those requirements", key="fretry", disabled=not reviewer):
                with st.spinner("Proposing specs for the missing requirements..."):
                    rep = forge.resume(cfg, audit, run_id)
                if rep.failed:
                    st.error("Still failing: " + json.dumps(rep.failed))
                st.rerun()
        again = forge.repropose_candidates(audit, run_id)
        if again and st.button(f"Propose again for {len(again)} specs (rejected, failing "
                               "checks, or requirement changed)",
                               key="frepro", disabled=not reviewer,
                               help="Asks the model again with the current prompt, for these "
                                    "specs only. Each answer becomes a new version for you to "
                                    "decide; approved specs are untouched."):
            with st.spinner("Proposing again..."):
                rep = forge.repropose(cfg, audit, run_id)
            if rep.failed:
                st.error("Failed: " + json.dumps(rep.failed))
            st.rerun()
        from harness.anvil import impact as fimpact
        made = {(c["payload"]["spec_item"], c["payload"].get("spec_version", 1)) for c in cases}
        ready = [s for s in specs if s["status"] == "approved" and not s["payload"]["problems"]
                 and (s["item_id"], s["version"]) not in made
                 and fimpact.spec_requirement_state(audit, s["payload"]) == "current"]
        if st.button(f"Generate cases for {len(ready)} approved specs", key="fgen",
                     disabled=not (reviewer and ready),
                     help="Code only, no model calls. Each spec's cases are also run against "
                          "simulated faults."):
            res = forge.generate(audit, run_id, reviewer)
            if res["skipped"]:
                st.warning(f"{len(res['skipped'])} specs skipped: code checks failed.")
            st.rerun()
        for s in specs:
            if s["payload"]["template"] in pick_t and (not only_bad or s["payload"]["problems"]):
                spec_card(s, db)
    with t2:
        if not cases:
            ui.empty("No cases yet", "Approve specs in tab 1, then generate.")
        by_spec: dict[str, list] = {}
        for c in cases:
            by_spec.setdefault(c["payload"]["spec_item"], []).append(c["payload"])
        tot = sum(f["total"] for f in faults.values())
        det = sum(f["detected"] for f in faults.values())
        if tot:
            st.metric("Injected faults detected by the generated cases", f"{det} of {tot}",
                      help="Each spec's cases run against a correct simulation and faulty "
                           "variants. This tests the tests, not the product.")
        from harness.anvil import impact as fimpact
        spec_by_id = {s["item_id"]: s for s in specs}
        state_of = {c["item_id"]: fimpact.case_state(audit, c, spec_by_id[c["payload"]["spec_item"]])
                    for c in cases}
        n_old = sum(1 for v in state_of.values() if v != "current")
        if n_old:
            st.warning(f"{n_old} cases are stale or superseded and are left out of exports.")
        cs_state = {c["payload"]["case_id"]: state_of[c["item_id"]] for c in cases}
        for spec_id, cs in by_spec.items():
            fc = faults.get(spec_id, {})
            head = f"**{cs[0]['requirement_id']}** · {cs[0]['template']} · {len(cs)} cases"
            if fc.get("total"):
                head += f" · detects {fc['detected']} of {fc['total']} injected faults"
            with st.container(border=True):
                st.markdown(head)
                if fc.get("reference_passes") is False:
                    st.error("A case fails on the correct simulation: the spec or the "
                             "generator is wrong. Do not use these cases.")
                for f in fc.get("faults", {}).values():
                    (st.caption if f["detected_by"] else st.warning)(
                        f"{'✓' if f['detected_by'] else '!'} {f['fault']}: "
                        + (", ".join(f["detected_by"]) if f["detected_by"]
                           else "no case detects this"))
                st.dataframe([{"Case": c["case_id"], "State": cs_state.get(c["case_id"]),
                               "Kind": c["kind"], "Title": c["title"],
                               "Expected": c["expected"], "Why": c["boundary_rationale"],
                               "Open values": "; ".join(c["open_values"])} for c in cs],
                             use_container_width=True, hide_index=True)
    with t3:
        st.write("Exports every generated case as JSON, Excel and a pytest module. The pytest "
                 "module is linted here and has not been run against any hardware.")
        if st.button("Export test cases", key="fexp", disabled=not (reviewer and cases)):
            st.session_state["last_export_f2"] = forge.export(audit, run_id, reviewer)
        res = st.session_state.get("last_export_f2")
        if res:
            st.success(f"Exported {res['count']} current cases"
                       + (f" ({res['left_out']} stale or superseded left out)"
                          if res.get("left_out") else "") + ". Lint: "
                       + ("clean" if not res["lint"] else "; ".join(res["lint"][:3])))
            for kind, path in res["files"].items():
                st.download_button(f"Download {kind.upper()}", Path(path).read_bytes(),
                                   file_name=Path(path).name, key=f"dlg-{kind}")
    with t4:
        audit_tab()
    st.stop()


# ---- Sift Delta runs: what changed between revisions -----------------------------------

DELTA_STATE = {"proposed": ("Open", "warn"), "edited": ("Open", "warn"),
               "approved": ("Needs action", "info"), "rejected": ("No action", "muted")}
DELTA_LABEL = {"changed": "Source changed", "moved": "Moved to another section",
               "removed": "Removed from source", "new_text": "New text, not yet extracted",
               "added": "Added"}


diff_html = ui.diff_html


def delta_card(item: dict) -> None:
    iid, p = item["item_id"], item["payload"]
    label, colour = DELTA_STATE[item["status"]]
    with st.container(border=True):
        who = p.get("requirement_id") or f"§{p.get('new_section') or '-'}"
        where = (f"§{p.get('old_section') or '-'} → §{p.get('new_section') or '-'}"
                 if p["kind"] in ("moved", "changed") else "")
        ui.card_head(who, [DELTA_LABEL.get(p["kind"], p["kind"]), where],
                     ui.badge(label, colour))
        if p.get("requirement_text"):
            st.caption(f"Approved requirement: {p['requirement_text']}")
        ui.text_html(diff_html(p["diff"]))
        s = sift_delta.summary(p)
        if s:
            st.caption("Code check: " + s + (f" · similarity {p['similarity']}"
                                             if p.get("similarity") is not None else ""))
        if p.get("note"):
            st.caption(p["note"])
        b = st.columns([1, 1, 3])
        if b[0].button("Needs action", key=f"a-{iid}", type="primary",
                       use_container_width=True,
                       disabled=not reviewer or item["status"] == "approved"):
            audit.decide(iid, "approved", reviewer)
            st.rerun()
        if b[1].button("No action", key=f"r-{iid}", use_container_width=True,
                       disabled=not reviewer or item["status"] == "rejected"):
            audit.decide(iid, "rejected", reviewer)
            st.rerun()


if workflow == "sift-delta":
    from harness.sift import delta as sift_delta

    meta = audit.get_item(f"DELTA-{run_id}")["payload"]
    ui.page_header("Sift Delta", f"{meta['base_file']} → {meta['new_file']}",
                   ("Base run " + meta["base_run"] + " · " if meta.get("base_run") else "")
                   + f"{meta['unchanged']} unchanged (not listed) · found by code, no model "
                     "calls")
    entries = audit.list_items(run_id, "delta_entry")
    td, ti, te, ta = st.tabs([f"Changes ({len(entries)})", "Impact on tests",
                              "Export and score", "Audit log"])
    with ti:
        from harness.anvil import impact as fimpact

        if meta.get("mode") != "spec":
            st.info("Impact on tests needs a spec comparison against an approved Sift run.")
        else:
            imp = fimpact.impact(audit, run_id)
            if not imp["forge_runs"]:
                st.info(f"No Anvil run has been built from Sift run {meta['base_run']}.")
            stale_n = sum(len(r["stale_cases"]) for r in imp["rows"])
            st.write(f"Anvil runs built from {meta['base_run']}: "
                     + (", ".join(imp["forge_runs"]) or "none")
                     + f". {stale_n} test cases rest on requirements whose source changed or "
                       "was removed.")
            if stale_n and st.button(f"Mark {stale_n} test cases stale", key="mstale",
                                     disabled=not reviewer,
                                     help="Recorded per case with this Delta as the reason. "
                                          "Stale cases are left out of Anvil exports."):
                n = fimpact.mark_stale(audit, run_id, reviewer)
                st.success(f"{n} cases marked stale.")
            if imp["rows"]:
                st.dataframe([{"Requirement": r["requirement_id"], "Change": r["kind"],
                               "Anvil run": r["forge_run"], "Cases": len(r["cases"]),
                               "Stale": len(r["stale_cases"])} for r in imp["rows"]],
                             use_container_width=True, hide_index=True)
            if imp["new_text"]:
                st.warning(f"{len(imp['new_text'])} new sentences in the revision have no "
                           "requirement and no test yet: "
                           + "; ".join(e["payload"]["new_text"][:80] for e in imp["new_text"]))
            ui.section("Update the changed requirements",
                       "A new version of the Sift requirement, approved here or in the Sift "
                       "run. Anvil then shows its spec as changed, to propose again.")
            for e in entries:
                ep = e["payload"]
                if ep["kind"] != "changed" or not ep.get("requirement_item"):
                    continue
                req = audit.get_item(ep["requirement_item"])
                rstatus = audit.status(req["item_id"])
                with st.container(border=True):
                    ui.card_head(ep["requirement_id"], [f"v{req['version']}"],
                                 status_badge(rstatus))
                    st.markdown(diff_html(ep["diff"]), unsafe_allow_html=True)
                    if req["payload"].get("delta_run") == run_id:
                        st.caption(f"Updated from this Delta: {req['payload']['text']}")
                        if rstatus != "approved":
                            b = st.columns([1, 1, 4])
                            decision_buttons(req["item_id"], b)
                        continue
                    proposal = fimpact.proposed_requirement_text(ep, req)
                    text = st.text_area(
                        "New requirement text", proposal or req["payload"]["text"],
                        key=f"ut-{e['item_id']}",
                        help="Pre-filled with the new source sentence when the requirement "
                             "repeated the old one word for word; otherwise edit it yourself.")
                    if proposal is None:
                        st.caption("The approved requirement was reworded from its source, so "
                                   "the new wording is yours to write.")
                    if st.button("Save as new requirement version", key=f"us-{e['item_id']}",
                                 disabled=not reviewer or text.strip() == req["payload"]["text"]):
                        fimpact.update_requirement(audit, req["item_id"], text.strip(), ep,
                                                   reviewer, run_id)
                        st.rerun()
    with td:
        c = st.columns(len(meta["counts"]) + 1 or 1)
        c[0].metric("Unchanged", meta["unchanged"])
        for col, (k, v) in zip(c[1:], meta["counts"].items(), strict=False):
            col.metric(DELTA_LABEL.get(k, k), v)
        kinds = sorted({e["payload"]["kind"] for e in entries})
        pick = st.multiselect("Show", kinds, default=kinds, key="dk",
                              format_func=lambda k: DELTA_LABEL.get(k, k))
        for e in entries:
            if e["payload"]["kind"] in pick:
                delta_card(e)
    with te:
        if st.button("Export changes (JSON, Excel)", key="export_d",
                     disabled=not (reviewer and entries)):
            st.session_state["last_export_d"] = sift_delta.export_delta(audit, run_id, reviewer)
        res = st.session_state.get("last_export_d")
        if res:
            st.success(f"Exported {res['count']} entries.")
            for kind, path in res["files"].items():
                st.download_button(f"Download {kind.upper()}", Path(path).read_bytes(),
                                   file_name=Path(path).name, key=f"dld-{kind}")
        st.divider()
        kp = PROJECT_ROOT / "data" / "synthetic" / "icx100_rev2_changes.json"
        key_path = st.text_input("Expected changes (JSON)",
                                 str(kp) if "icx100" in meta["new_file"] else "", key="dkey")
        if key_path and Path(key_path).exists() and st.button("Score", key="dscore"):
            s = sift_delta.score(audit, run_id, key_path)
            st.markdown(f"**{s['found']} of {s['expected']}** expected changes found "
                        f"({s['entries']} entries listed).")
            for m in s["missed"]:
                st.caption(f"Missed: {m['kind']} · {m.get('what', '')}")
    with ta:
        audit_tab()
    st.stop()


# ---- smoke runs: single list ------------------------------------------------------------

if workflow not in {pipeline.WORKFLOW, *pipeline.LEGACY_WORKFLOWS}:
    reqs = audit.list_items(run_id, "requirement")
    counts_row(reqs)
    for it in reqs:
        requirement_card(it)
    with st.expander("Audit log for this run"):
        audit_tab()
    st.stop()

# ---- Sift runs: one tab per stage ---------------------------------------------------

doc = audit.get_item(f"DOC-{run_id}")["payload"]
ui.page_header("Sift", doc["title"],
               f"{doc['filename']} · converter: {doc['converter']} · sha256 "
               f"{doc['sha256'][:16]}… · taxonomy: {TAX.label}")
maps = sorted(audit.list_items(run_id, "section_mapping"), key=doc_order)
reqs = sorted(audit.list_items(run_id, "requirement"), key=doc_order)
t1, t2, t3, t4 = st.tabs([f"1. Section mapping ({len(maps)})", f"2. Requirements ({len(reqs)})",
                          "3. Export", "Audit log"])

with t1:
    counts_row(maps)
    pending_hi = [m for m in maps if m["status"] in ("proposed", "edited")
                  and m["payload"]["confidence"] >= 0.9]
    if pending_hi:
        st.caption("The rating is the model's own estimate. It has not been shown to predict "
                   "correctness, so read the section previews before approving in bulk.")
    if pending_hi and st.button(f"Approve all {len(pending_hi)} pending mappings the model "
                                "rated 0.90 or above", key="bulk", disabled=not reviewer):
        for m in pending_hi:
            audit.decide(m["item_id"], "approved", reviewer,
                         comment="bulk approval, model self-rating >= 0.90")
        st.rerun()
    for it in maps:
        mapping_card(it)

with t2:
    approved_maps = [m for m in maps if m["status"] == "approved"
                     and m["payload"]["subsystem_id"] != "NONE"]
    extracted = {r["payload"]["section_id"] for r in reqs} | {
        e["detail"]["section_id"] for e in run_events
        if e["action"] == "extracted_none" and e["detail"]}
    waiting = [m for m in approved_maps if m["payload"]["section_id"] not in extracted]
    st.caption(f"{len(approved_maps)} approved sections with requirements · "
               f"{len(waiting)} waiting for extraction. Only approved mappings are extracted.")
    if waiting and not reviewer:
        st.warning("Enter your name in the sidebar to enable extraction.")
    if st.button(f"Extract requirements from {len(waiting)} approved sections",
                 key="extract", disabled=not (reviewer and waiting)):
        with st.spinner("Extracting and running the AI reviewer, section by section..."):
            rep = pipeline.extract(cfg, audit, run_id)
        audit.log_event(reviewer, "stage_started", run_id=run_id,
                        detail={"stage": "extract", **rep.as_dict()})
        if rep.failed:
            st.error("Failed sections: " + json.dumps(rep.failed))
        st.rerun()

    if reqs:
        counts_row(reqs)
        f1, f2 = st.columns(2)
        subs = sorted({r["payload"]["subsystem_id"] for r in reqs})
        pick_sub = f1.multiselect("Subsystem", subs, default=subs, key="fsub")
        pick_status = f2.multiselect("Status", STATUSES, default=STATUSES,
                                     key="fstat")
        attention = st.toggle("Only items needing attention (a check failed or the AI objected)",
                              key="fattn")
        clean = [r for r in reqs if r["status"] in ("proposed", "edited")
                 and audit.latest_ai_review(r["item_id"]) and not needs_attention(r)]
        if clean:
            with st.expander(f"Approve {len(clean)} requirements where every check passed and "
                             "the AI reviewer accepted"):
                st.caption("Concrete checks only: quote located, modal verb kept, values from "
                           "the source, vague words flagged, no open placeholders, AI accepted. "
                           "Read them before ticking the box.")
                for r in clean:
                    st.write(f"{pipeline.display_id(r['item_id'])}: {r['payload']['text']}")
                read = st.checkbox(f"I have read these {len(clean)} requirements",
                                   key="bulkread")
                if st.button("Approve them", key="bulkreq",
                             disabled=not (reviewer and read)):
                    for r in clean:
                        audit.decide(r["item_id"], "approved", reviewer,
                                     comment="bulk approval: every check passed, AI accepted")
                    st.rerun()
        to_clarify = pipeline.clarify_candidates(audit, run_id)
        if st.button(f"Propose clarifications for {len(to_clarify)} flagged requirements",
                     key="clarify", disabled=not (reviewer and to_clarify),
                     help="Asks the generator model how vague source wording could be made "
                          "testable. Missing values come back as <TBD: ...> placeholders, "
                          "never invented. Advice only."):
            with st.spinner("Proposing clarifications, section by section..."):
                rep = pipeline.clarify(cfg, audit, run_id)
            audit.log_event(reviewer, "stage_started", run_id=run_id,
                            detail={"stage": "clarify", **rep.as_dict()})
            if rep.failed:
                st.error("Failed sections: " + json.dumps(rep.failed))
            st.rerun()
        missed = [e for e in run_events if e["action"] == "ai_review_missed"]
        if missed:
            with st.expander(f"AI reviewer: possible missed requirements ({len(missed)} sections)"):
                for e in missed:
                    for m in e["detail"]["missed"]:
                        st.write(f"- §{e['detail']['section_id']}: {m}")
        for it in reqs:
            if (it["payload"]["subsystem_id"] in pick_sub and it["status"] in pick_status
                    and (not attention or needs_attention(it))):
                requirement_card(it)

with t3:
    approved = [r for r in reqs if r["status"] == "approved"]
    st.write(f"{len(approved)} approved of {len(reqs)} requirements. Only approved "
             "requirements are exported.")
    if st.button("Export JSON, Excel and ReqIF", key="export",
                 disabled=not (reviewer and approved)):
        res = export(audit, run_id, reviewer)
        st.session_state["last_export"] = res
    res = st.session_state.get("last_export")
    if res:
        st.success(f"Exported {res['count']} requirements.")
        for kind, path in res["files"].items():
            st.download_button(f"Download {kind.upper()}", Path(path).read_bytes(),
                               file_name=Path(path).name, key=f"dl-{kind}")

with t4:
    audit_tab()
