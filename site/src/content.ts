// Every claim and number on the page comes from the Zyn README and benchmark wiki.
// Change a figure there first, then here.



export const PILLARS = [
  { icon: "code-check", title: "Caught by code.", text: "Changed numbers, invented values, weakened wording, tests that can never fail. Same input, same result, every run." },
  { icon: "ai-reviewer", title: "Advice with quotes.", text: "Every AI finding must quote the words it rests on. Code confirms the quote is there before you see it." },
  { icon: "person", title: "A named person decides.", text: "Nothing is approved until a person approves it. The AI reviewer can never approve." },
  { icon: "audit-log", title: "A record that holds.", text: "Every proposal, check and decision lands in an append-only audit log you can export." },
];

export const STUDY = [
  { label: "Inspecting and correcting AI output is the biggest cost", n: 14 },
  { label: "Reviewing existing work is the use they want most", n: 10 },
  { label: "Plausible false facts are a reason to reject the tool", n: 9 },
];

export type Layer = {
  id: string;
  icon: string;
  title: string;
  short: string;
  text: string;
  record: { k: string; v: string; tone?: "bad" | "ok" | "warn" | "muted" }[];
};

export const LAYERS: Layer[] = [
  {
    id: "code",
    icon: "code-check",
    title: "Code checks",
    short: "Decide what they can prove",
    text: "Deterministic checks run first. No model, no key, no cost. A number that changed or a signal that does not exist fails here, the same way every time.",
    record: [
      { k: "check", v: "number_changed" },
      { k: "source", v: "\"within 10 ms\"" },
      { k: "item", v: "\"within 20 ms\"" },
      { k: "result", v: "failed", tone: "bad" },
      { k: "who", v: "code check", tone: "muted" },
    ],
  },
  {
    id: "ai",
    icon: "ai-reviewer",
    title: "AI reviewer",
    short: "Advises, and only with quotes",
    text: "A second model reads the work and raises findings. A finding without a quote that code can locate in the source is never shown. It can advise. It cannot approve.",
    record: [
      { k: "finding", v: "weakened_modal" },
      { k: "quote", v: "\"should\"" },
      { k: "quote_found", v: "true", tone: "ok" },
      { k: "role", v: "advice", tone: "warn" },
      { k: "who", v: "AI reviewer", tone: "muted" },
    ],
  },
  {
    id: "person",
    icon: "person",
    title: "A named person",
    short: "Makes every final call",
    text: "The reviewer sees the item, the quoted evidence and which checks passed. One key to approve, one to reject, and every decision can be undone.",
    record: [
      { k: "decision", v: "rejected" },
      { k: "reason", v: "value not in source" },
      { k: "by", v: "named reviewer" },
      { k: "undo", v: "adds a record", tone: "muted" },
    ],
  },
  {
    id: "log",
    icon: "audit-log",
    title: "Audit log",
    short: "Remembers who and when",
    text: "Every step is appended, never overwritten. Undoing a decision adds a record rather than erasing one. Export it as an evidence report and an assessor checklist.",
    record: [
      { k: "0412", v: "proposed   REQ-014" },
      { k: "0413", v: "check      number_changed  failed", tone: "bad" },
      { k: "0414", v: "advice     weakened_modal  quoted", tone: "warn" },
      { k: "0415", v: "decided    rejected" },
      { k: "0416", v: "export     evidence report", tone: "muted" },
    ],
  },
];

export type ProofRow = { mistake: string; caught: number; of: number; note?: string };

export const CAUGHT: ProofRow[] = [
  { mistake: "A number in a requirement changed (10 becomes 20)", caught: 21, of: 22 },
  { mistake: "A timing value added that the source never gives", caught: 150, of: 156, note: "all 156 flagged" },
  { mistake: "\"shall\" weakened to \"should\"", caught: 146, of: 153 },
  { mistake: "A requirement the source doesn't contain", caught: 8, of: 8 },
  { mistake: "A misspelt or out-of-range signal in a test", caught: 68, of: 68 },
  { mistake: "A test citing a requirement that doesn't exist, or none", caught: 86, of: 86 },
  { mistake: "A test whose checks were deleted, so it can never fail", caught: 40, of: 40 },
  { mistake: "A faulty CAN database (10 kinds of fault)", caught: 10, of: 10 },
];

export const STOPS: ProofRow[] = [
  { mistake: "A signal or status name swapped for another valid one", caught: 1, of: 52, note: "A person catches it" },
  { mistake: "A test's expected on/off value flipped", caught: 0, of: 15, note: "The fault-kill simulation in Anvil" },
];

export const TEMPLATES: ProofRow[] = [
  { mistake: "Zyn template path (Anvil)", caught: 30, of: 31 },
  { mistake: "Sonnet, best of two runs", caught: 26, of: 31, note: "25 and 26" },
  { mistake: "Opus, best of two runs", caught: 25, of: 31, note: "25 and 23" },
  { mistake: "Haiku, best of two runs", caught: 22, of: 31, note: "22 and 21" },
];

export type Tool = {
  id: string;
  name: string;
  mark: string;
  text: string;
  inputs: string[];
  outputs: string[];
  planned?: boolean;
};

export const TOOLS: Tool[] = [
  { id: "sift", name: "Sift", mark: "sift", text: "Turns a specification into requirements, each tied to the source words it came from.", inputs: ["PDF", "DOCX", "Markdown"], outputs: ["ReqIF", "Excel"] },
  { id: "sift-review", name: "Sift Review", mark: "sift", text: "Reviews a requirement set you already have against its source.", inputs: ["ReqIF", "Excel", "CSV"], outputs: ["ReqIF", "Evidence report"] },
  { id: "sift-delta", name: "Sift Delta", mark: "sift", text: "Shows what changed between two revisions, and which approved requirements it touches.", inputs: ["PDF", "DOCX"], outputs: ["ReqIF", "Excel"] },
  { id: "anvil", name: "Anvil", mark: "anvil", text: "Builds test cases by code from checked templates, then scores them against injected faults.", inputs: ["ReqIF", "DBC"], outputs: ["pytest", "Robot", "CAPL"] },
  { id: "anvil-review", name: "Anvil Review", mark: "anvil", text: "Checks tests from any tool against a CAN database and the requirements they claim to cover.", inputs: ["DBC", "CSV"], outputs: ["Evidence report", "Excel"] },
  { id: "assay", name: "Assay", mark: "assay", text: "Benchmarks any model on public answer keys: accuracy, repeatability and cost per correct answer.", inputs: ["Answer keys"], outputs: ["Excel"] },
  { id: "scribe", name: "Scribe", mark: "scribe", text: "Documents. Planned.", inputs: [], outputs: [], planned: true },
  { id: "source", name: "Source", mark: "source", text: "Procurement. Planned.", inputs: [], outputs: [], planned: true },
];

// The hub: what goes in on the left, what comes out on the right.
export const HUB_IN = ["PDF", "DOCX", "Markdown", "ReqIF", "Excel", "CSV", "DBC", "Answer keys"];
export const HUB_OUT = ["ReqIF", "Excel", "pytest", "Robot", "CAPL", "Evidence report"];

export const WHY = [
  { title: "Works on anyone's output", text: "Requirements and tests from any tool or any person. You don't have to generate with Zyn to check with Zyn." },
  { title: "Quotes verified by code", text: "An AI finding without a quote that code can locate is never shown." },
  { title: "No silent pass", text: "Empty or junk input is refused or reported as skipped. It is never passed." },
  { title: "Decisions persist", text: "Dismiss a finding once. It stays dismissed on later runs of the same text." },
  { title: "Four eyes by default", text: "In a team, nobody approves their own work. Every decision records who made it and which rule applied." },
  { title: "Your servers, your sign-in", text: "Run it for a team in your own network or cloud, with company sign-in, roles per programme and a shared append-only log." },
  { title: "Fits your toolchain", text: "ReqIF round-trip to DOORS Next, Polarion and Codebeamer. Tests out to pytest, Robot Framework and CAPL. Evidence reports for assessors." },
  { title: "Runs inside an agent", text: "The same checks are an MCP server, so an agent can check its own work before it hands it over." },
  { title: "Your models, your walls", text: "One setting refuses every cloud call. IT lists the models a team may use. Zyn sends nothing home." },
];

export const LIMITS = [
  "Prototype. Every screen and export says so.",
  "Public and synthetic data only. No company or customer documents.",
  "The ICX-100 answer key was written by Claude and checked by an AI reviewer, not an engineer.",
  "No productivity claims. No benchmark here measures time saved.",
  "Team mode is new. The container and real company sign-in have not yet been tried end to end.",
  "Not a qualified tool under ISO 26262. A draft tool confidence argument exists; a safety engineer has not reviewed it.",
];

export const FAQ = [
  { q: "Do I have to generate with Zyn to use it?", a: "No. Sift Review and Anvil Review check work from any tool or person. That is the main use." },
  { q: "Does my data leave my machine?", a: "Only if you let it. The code checks never call a model. Set offline mode and every cloud call is refused; local models run through Ollama. Zyn sends nothing to its makers." },
  { q: "Can a whole team use it?", a: "Yes. Team mode runs on a server in your network or cloud account, with company sign-in, roles per programme, a shared PostgreSQL audit log and four eyes on by default." },
  { q: "Why no confidence score?", a: "A model's rating of itself has not been shown to predict correctness. Zyn shows checks that passed or failed, and quotes you can read." },
  { q: "The AI reviewer gives different answers each run. How is that handled?", a: "Zyn measures it instead of hiding it. Run several passes and see how many reported each finding. Your decisions carry over between runs." },
  { q: "Will it save my team time?", a: "We don't claim a number. That needs a pilot with real engineers on real work. What Zyn measures is what it catches and what it misses." },
];

// Hero lanes: records flowing through the checks. Each has the verdict it gets at the gate.
export type LaneItem = { id: string; text: string; verdict: "pass" | "hatch" | "cross" };
export const LANES: LaneItem[][] = [
  [
    { id: "REQ-014", text: "within 20 ms", verdict: "cross" },
    { id: "REQ-015", text: "shall display", verdict: "pass" },
    { id: "REQ-016", text: "shall warn", verdict: "pass" },
    { id: "REQ-017", text: "should flash", verdict: "hatch" },
    { id: "REQ-018", text: "shall log", verdict: "pass" },
    { id: "REQ-019", text: "shall dim", verdict: "pass" },
  ],
  [
    { id: "TC-201", text: "EngSpeed > 6000", verdict: "pass" },
    { id: "TC-202", text: "VehSpd_Kmh", verdict: "pass" },
    { id: "TC-203", text: "FuelLvl_Pct", verdict: "pass" },
    { id: "TC-204", text: "no checks left", verdict: "cross" },
    { id: "TC-205", text: "DoorAjar", verdict: "pass" },
    { id: "TC-206", text: "cites REQ-099", verdict: "cross" },
  ],
  [
    { id: "BO_ 0x1A0", text: "EngData", verdict: "pass" },
    { id: "SG_ OilTemp", text: "0 to 300", verdict: "hatch" },
    { id: "BO_ 0x2B4", text: "Cluster", verdict: "pass" },
    { id: "SG_ Gear", text: "bits overlap", verdict: "cross" },
    { id: "BO_ 0x3C1", text: "Lamps", verdict: "pass" },
    { id: "SG_ Odo", text: "0 to 999999", verdict: "pass" },
  ],
];

export const SECTIONS = [
  { id: "problem", label: "The problem" },
  { id: "how", label: "How it works" },
  { id: "proof", label: "The proof" },
  { id: "tools", label: "The tools" },
  { id: "why", label: "Why Zyn" },
  { id: "contribute", label: "Contribute" },
];
