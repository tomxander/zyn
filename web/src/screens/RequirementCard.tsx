// A requirement extracted by Sift: text, source, checks, AI verdict, clarification, decision.

import { Pencil, RotateCcw, Sparkles, WandSparkles } from "../components/icons";
import { useState, memo } from "react";
import { useConfig, useEdit } from "../lib/api";
import { useReviewer } from "../lib/reviewer";
import { DecisionBar } from "../components/Decision";
import { Drawer } from "../components/Drawer";
import { Button, Card, CardHead, Checks, Diff, Field, ItemText, Msg, Quote, Select,
  StatusBadge } from "../components/ui";


function RequirementCardInner({ c, index }: { c: any; index: number }) {
  const p = c.payload;
  const r = c.review;
  const { canAct, noActReason } = useReviewer();
  const edit = useEdit();
  const [open, setOpen] = useState(false);
  const where = [p.page && `page ${p.page}`,
    p.quote_offset && `characters ${p.quote_offset[0]}-${p.quote_offset[1]} of the section`].filter(Boolean).join(" · ");
  // "unknown" and "none" say nothing; show the hint only when the model named a level.
  const asil = p.asil_hint && !["unknown", "none", "n/a"].includes(String(p.asil_hint).toLowerCase()) ? p.asil_hint : null;

  return (
    <Card index={index} label={c.display_id}>
      <CardHead id={c.display_id} meta={[`v${c.version}`, p.section_number && `§${p.section_number}`,
        p.subsystem_id, p.req_type, p.modal, p.verification_method]} badge={<StatusBadge status={c.status} />} />
      <ItemText>{p.text}</ItemText>
      <Quote>Source: “{p.source_quote}”{where && <span className="quiet"> ({where})</span>}</Quote>
      {c.diff && <p className="small"><span className="quiet">Changed from the extracted version: </span><Diff ops={c.diff} /></p>}
      <Checks items={c.checks} />
      {(c.flags.length > 0 || asil) && <p className="small quiet">
        {c.flags.length > 0 && <>Quality flags: {c.flags.join(", ")}</>}
        {c.flags.length > 0 && asil && " · "}
        {asil && <>ASIL hint (model suggestion): {asil}</>}</p>}

      {p.grounded === false && <Msg tone="bad">Ungrounded: the quote was not found in the source section (code check).</Msg>}
      {p.modal_changed && <Msg tone="bad">Modal verb changed from the source (code check).</Msg>}
      {p.weak_word_unflagged && <Msg tone="warn">Weak words in the source not flagged by the model: {(p.weak_words_found ?? []).join(", ")} (code check).</Msg>}
      {/* An accept is already the "AI reviewer accepted" check chip; only objections get a message. */}
      {r && r.verdict !== "accept" && (
        <Msg tone="warn">
          <span className="who">AI reviewer ({r.actor}, on v{r.on_version}) </span><b>{r.verdict}</b>
          {r.objection_scope === "labels" && " · about labels only, the text is fine"}
          {r.objection_scope === "text" && " · about the requirement text"}
          {r.issues?.length > 0 && <ul>{r.issues.map((x: string) => <li key={x}>{x}</li>)}</ul>}
          {r.suggested_text && <div>Suggested text: {r.suggested_text}</div>}
          {r.suggested_req_type && <div>Suggested type: {r.suggested_req_type}</div>}
          {r.suggested_flags && <div>Suggested flags: {r.suggested_flags.join(", ") || "none"}</div>}
        </Msg>
      )}
      {c.clarification && (
        <Msg tone="info">
          <span className="who">Proposed clarification ({c.clarification.actor}, advice for you and the spec author) </span>
          <b>{c.clarification.proposed_text}</b>
          <div>Resolves: {c.clarification.resolves.join(", ") || "none"}</div>
          <div className="quiet">{c.clarification.rationale}</div>
          {c.clarification.open_questions.length > 0 && <>
            <div>Questions for the spec author:</div>
            <ul>{c.clarification.open_questions.map((q: string) => <li key={q}>{q}</li>)}</ul></>}
        </Msg>
      )}
      {c.clarification?.problems?.length > 0 && <Msg tone="bad">Clarification cannot be used with one click (code check): {c.clarification.problems.join("; ")}. Use Edit if part of it is right.</Msg>}
      {c.open_placeholders.length > 0 && <Msg tone="warn">{c.open_placeholders.length === 1 ? "1 placeholder" : `${c.open_placeholders.length} placeholders`} still open: {c.open_placeholders.join(", ")}. Fill them with Edit once the spec author answers, or approve with them as open items.</Msg>}
      {p.clarification?.open_questions?.length > 0 && <p className="small quiet">Open questions carried into export: {p.clarification.open_questions.join("; ")}</p>}
      {c.own_problems.length > 0 && <Msg tone="bad">This version's text fails the code check: {c.own_problems.join("; ")}. Revert to original or edit it.</Msg>}
      {c.suggestion_problems.length > 0 && <Msg tone="bad">AI suggestion cannot be applied with one click (code check): {c.suggestion_problems.join("; ")}. Use Edit if part of it is right.</Msg>}

      <DecisionBar itemId={c.item_id} decision={c.decision} extra={<>
        {c.can_apply && <Button icon={WandSparkles} disabled={!canAct} tip={!canAct ? noActReason : undefined}
          onClick={() => edit.mutate({ item_id: c.item_id, kind: "apply_suggestion" })}>Apply AI suggestion</Button>}
        {c.clarification && !c.clarification.problems.length && <Button icon={Sparkles} disabled={!canAct} tip={!canAct ? noActReason : undefined}
          onClick={() => edit.mutate({ item_id: c.item_id, kind: "use_clarification" })}>Use clarification</Button>}
        {c.version > 1 && <Button variant="ghost" icon={RotateCcw} disabled={!canAct} tip={!canAct ? noActReason : undefined}
          onClick={() => edit.mutate({ item_id: c.item_id, kind: "revert" })}>Revert to original</Button>}
        <Button variant="ghost" icon={Pencil} className="push" data-key="e" onClick={() => setOpen(true)}>Edit</Button>
      </>} />
      {/* Keyed by version: after an edit or a one-click fix the form starts from the new text. */}
      <EditRequirement key={c.version} c={c} open={open} onOpenChange={setOpen} />
    </Card>
  );
}

function EditRequirement({ c, open, onOpenChange }: { c: any; open: boolean; onOpenChange: (v: boolean) => void }) {
  const p = c.payload;
  const { canAct, noActReason } = useReviewer();
  const edit = useEdit();
  const [text, setText] = useState(p.text);
  const [type, setType] = useState(p.req_type);
  const [modal, setModal] = useState(p.modal);
  const [flags, setFlags] = useState<string[]>(c.flags);
  const [note, setNote] = useState("");
  const enums = useConfig().data?.enums ?? { req_type: [], modal: [], quality_flag: [] };
  const REQ_TYPES: string[] = enums.req_type, MODALS: string[] = enums.modal, FLAGS: string[] = enums.quality_flag;
  return (
    <Drawer open={open} onOpenChange={onOpenChange} title={`Edit ${c.display_id}`}
      description="Saved as a new version. The extracted version stays in the record."
      footer={<>
        <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant="primary" disabled={!canAct} tip={!canAct ? noActReason : undefined} busy={edit.isPending} onClick={() => edit.mutate(
          { item_id: c.item_id, kind: "edit", comment: note, fields: { text, req_type: type, quality_flags: flags, ...(p.modal ? { modal } : {}) } },
          { onSuccess: () => onOpenChange(false) })}>Save as new version</Button>
      </>}>
      <Quote>Source: “{p.source_quote}”</Quote>
      <Field label="Requirement text"><textarea className="textarea" value={text} onChange={(e) => setText(e.target.value)} /></Field>
      <div className="fields">
        <Field label="Type"><Select value={type} onChange={setType} options={REQ_TYPES.map((t) => ({ value: t, label: t }))} /></Field>
        {p.modal && <Field label="Modal"><Select value={modal} onChange={setModal} options={MODALS.map((t) => ({ value: t, label: t }))} /></Field>}
      </div>
      <Field label="Quality flags">
        <div className="filter-group">
          {FLAGS.map((f) => (
            <button key={f} className="filter" aria-pressed={flags.includes(f)}
              onClick={() => setFlags(flags.includes(f) ? flags.filter((x) => x !== f) : [...flags, f])}>{f}</button>
          ))}
        </div>
      </Field>
      <Field label="Reason for edit"><input className="input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
    </Drawer>
  );
}

/** Memoised: a decision on one card does not re-render the others. */
export const RequirementCard = memo(RequirementCardInner);
