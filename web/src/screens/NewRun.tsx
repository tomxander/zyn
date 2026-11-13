// Start a new run: one drawer, one form per tool.

import { Anvil, Sift, Upload, type ZynIconType } from "../components/icons";
import { useState } from "react";
import { toast } from "sonner";
import { api, useConfig, type Job } from "../lib/api";
import { useAddJob } from "../lib/jobs";
import { useReviewer } from "../lib/reviewer";
import { Drawer } from "../components/Drawer";
import { Button, Field, Select } from "../components/ui";

type Kind = "sift" | "check" | "tests" | "delta" | "forge";
// Grouped by family: the Sift tools, then the Anvil tools. Each shows its family's mark.
const KINDS: { kind: Kind; title: string; text: string; icon: ZynIconType }[] = [
  { kind: "sift", title: "Sift", text: "Extract requirements from a specification", icon: Sift },
  { kind: "check", title: "Sift Review", text: "Check an existing requirement set", icon: Sift },
  { kind: "delta", title: "Sift Delta", text: "What changed between revisions", icon: Sift },
  { kind: "forge", title: "Anvil", text: "Test cases from an approved Sift run", icon: Anvil },
  { kind: "tests", title: "Anvil Review", text: "Check tests from any tool against a CAN database and requirements", icon: Anvil },
];

function FilePick({ label, accept, file, onFile }: { label: string; accept: string; file?: File; onFile: (f?: File) => void }) {
  return (
    <Field label={label}>
      <label className="btn btn-file">
        <Upload aria-hidden />{file ? file.name : "Choose file"}
        <input type="file" accept={accept} className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
      </label>
    </Field>
  );
}

export function NewRun({ open, onOpenChange, onStarted }: {
  open: boolean; onOpenChange: (v: boolean) => void; onStarted: (runId: string | null) => void;
}) {
  const { reviewer } = useReviewer();
  const cfg = useConfig();
  const addJob = useAddJob();
  const [kind, setKind] = useState<Kind>("sift");
  const [files, setFiles] = useState<Record<string, File | undefined>>({});
  const [base, setBase] = useState<string>();
  const [mode, setMode] = useState<"spec" | "set">("spec");
  const [rules, setRules] = useState("default");
  const [busy, setBusy] = useState(false);
  const sift = (cfg.data?.sift_runs ?? []) as string[];
  const f = (k: string) => (v?: File) => setFiles((s) => ({ ...s, [k]: v }));

  const ready = kind === "sift" || kind === "check" || kind === "tests" ? !!files.file
    : kind === "forge" ? !!base : mode === "spec" ? !!(base && files.new) : !!(files.old && files.new);

  async function submit() {
    const fd = new FormData();
    fd.set("reviewer", reviewer);
    Object.entries(files).forEach(([k, v]) => v && fd.set(k, v));
    if (base) fd.set("base", base);
    fd.set("mode", mode);
    fd.set("rules", rules);
    setBusy(true);
    try {
      const res = await api<any>(`/api/new/${kind}`, { method: "POST", body: fd });
      if (res.job) {
        addJob("new", res.job as Job);
        toast("Started. Progress shows on the page.");
        onStarted(null);
      } else {
        toast.success("Run created");
        onStarted(res.run_id);
      }
      setFiles({});
      onOpenChange(false);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange} title="Start new run"
      description="Each run is recorded in the audit log under your name."
      footer={<>
        <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant="primary" disabled={!ready || !reviewer} busy={busy} onClick={submit}>Start</Button>
      </>}>
      <div className="filter-group" data-marks role="radiogroup" aria-label="Tool">
        {KINDS.map((k) => (
          <button key={k.kind} className="filter" aria-pressed={kind === k.kind} onClick={() => setKind(k.kind)}>
            <k.icon size={14} aria-hidden />{k.title}
          </button>
        ))}
      </div>
      <p className="small quiet">{KINDS.find((k) => k.kind === kind)!.text}.</p>

      {kind === "sift" && <FilePick label="Specification (PDF, DOCX, Markdown, text)" accept=".pdf,.docx,.md,.txt" file={files.file} onFile={f("file")} />}
      {kind === "check" && <>
        <FilePick label="Requirement set (ReqIF, Excel, CSV)" accept=".reqif,.xlsx,.csv" file={files.file} onFile={f("file")} />
        <Field label="Rule profile (code checks)">
          <Select value={rules} onChange={setRules}
            options={((cfg.data?.rule_profiles ?? [{ name: "default", description: "" }]) as any[])
              .filter((r) => !r.broken)
              .map((r) => ({ value: r.name, label: r.description ? `${r.name}: ${r.description}` : r.name }))} />
        </Field>
        <p className="small quiet">Profiles are YAML files in rules/. They choose which code checks run and tune the weak-word list; the AI reviewer is not affected.</p>
        <FilePick label="Source specification, optional (PDF, DOCX, Markdown, text)" accept=".pdf,.docx,.md,.txt" file={files.source} onFile={f("source")} />
        <p className="small quiet">With the source, code matches each requirement to a source sentence and flags requirements with no match, invented values and changed modal verbs. Use it for sets another tool or model produced.</p>
      </>}
      {kind === "tests" && <>
        <FilePick label="Test file (pytest, CAPL, Robot Framework, text)" accept=".py,.can,.cin,.robot,.txt,.md,.csv,.json" file={files.file} onFile={f("file")} />
        <FilePick label="CAN database (DBC, KCD, SYM or ARXML). Leave empty for the synthetic ICX-100 one" accept=".dbc,.kcd,.sym,.arxml" file={files.dbc} onFile={f("dbc")} />
        <FilePick label="Requirement set the tests refer to, optional (ReqIF, Excel, CSV)" accept=".reqif,.xlsx,.csv" file={files.reqs} onFile={f("reqs")} />
        <p className="small quiet">Code only, no model calls. The CAN database is checked first (duplicate frame IDs, overlapping bits, impossible ranges). Then each test: signal names and ranges, requirement references, values not in the requirement, exact comparisons with no tolerance, missing setup and duplicate tests. Coverage: requirements no test covers and signal limits never tested.</p>
      </>}
      {kind === "delta" && <>
        <div className="filter-group">
          <button className="filter" aria-pressed={mode === "spec"} onClick={() => setMode("spec")}>New revision of an extracted spec</button>
          <button className="filter" aria-pressed={mode === "set"} onClick={() => setMode("set")}>Two requirement sets</button>
        </div>
        {mode === "spec" ? <>
          <Field label="Approved Sift run"><Select value={base} onChange={setBase} placeholder="Choose a run" options={sift.map((s) => ({ value: s, label: s }))} /></Field>
          <FilePick label="New revision (PDF, DOCX, Markdown, text)" accept=".pdf,.docx,.md,.txt" file={files.new} onFile={f("new")} />
        </> : <>
          <FilePick label="Old set (ReqIF, Excel, CSV)" accept=".reqif,.xlsx,.csv" file={files.old} onFile={f("old")} />
          <FilePick label="New set (ReqIF, Excel, CSV)" accept=".reqif,.xlsx,.csv" file={files.new} onFile={f("new")} />
        </>}
      </>}
      {kind === "forge" && <>
        <Field label="Approved Sift run"><Select value={base} onChange={setBase} placeholder="Choose a run" options={sift.map((s) => ({ value: s, label: s }))} /></Field>
        <FilePick label="CAN database (DBC). Leave empty for the synthetic ICX-100 one" accept=".dbc" file={files.dbc} onFile={f("dbc")} />
        <p className="small quiet">One model call per section. Code then checks every proposal.</p>
      </>}
    </Drawer>
  );
}
