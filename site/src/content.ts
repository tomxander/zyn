// Every claim and number on the page comes from the Zyn README and benchmark wiki.
// Change a figure there first, then here.



export const PILLARS = [
  { icon: "code-check", title: "See what changed.", text: "Numbers, limits and \"shall\" compared with the source. No AI needed, and the same answer every run." },
  { icon: "ai-reviewer", title: "Advice you can check.", text: "The AI reviewer must quote the line its concern rests on, or you never see it." },
  { icon: "person", title: "You make the call.", text: "Nothing is approved until a named engineer approves it. The AI can't." },
  { icon: "audit-log", title: "A record that holds.", text: "Every decision is kept with who made it and when, ready when the assessor asks." },
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
    short: "Flag what they can find",
    text: "Runs first, with no AI, no key and no cost. A changed number, an invented value or a signal that doesn't exist is flagged, the same way every time.",
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
    text: "A second AI reads the work and raises concerns. If it can't quote the exact words a concern rests on, you never see it. It advises. It can't approve.",
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
    text: "You see the item, the evidence and what the checks found. One key to approve, one to reject, and any decision can be undone.",
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
    text: "Every step is added, never overwritten: in team mode the database refuses edits and deletes; in desk mode the evidence export's hash chain shows any change. Export it as an evidence report when the assessor asks.",
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
  { id: "sift-review", name: "Sift Review", mark: "sift", text: "Check a requirement set from a supplier or AI tool against its specification.", inputs: ["ReqIF", "Excel", "CSV"], outputs: ["ReqIF", "Evidence report"] },
  { id: "anvil-review", name: "Anvil Review", mark: "anvil", text: "Find tests that name signals that don't exist, cite missing requirements or can never fail.", inputs: ["DBC", "CSV"], outputs: ["Evidence report", "Excel"] },
  { id: "sift-delta", name: "Sift Delta", mark: "sift", text: "A new spec revision? See every change, and which approved requirements it touches.", inputs: ["PDF", "DOCX"], outputs: ["ReqIF", "Excel"] },
  { id: "sift", name: "Sift", mark: "sift", text: "Draft requirements from a specification, each tied to the words it came from.", inputs: ["PDF", "DOCX", "Markdown"], outputs: ["ReqIF", "Excel"] },
  { id: "anvil", name: "Anvil", mark: "anvil", text: "Build tests from checked templates, and see which planted faults they catch.", inputs: ["ReqIF", "DBC"], outputs: ["pytest", "Robot", "CAPL"] },
  { id: "assay", name: "Assay", mark: "assay", text: "Compare Claude and local Ollama models on public tests: accuracy, consistency and cost per right answer.", inputs: ["Answer keys"], outputs: ["Excel"] },
  { id: "scribe", name: "Scribe", mark: "scribe", text: "Documents. Planned.", inputs: [], outputs: [], planned: true },
  { id: "source", name: "Source", mark: "source", text: "Procurement. Planned.", inputs: [], outputs: [], planned: true },
];

// The hub: what goes in on the left, what comes out on the right.
export const HUB_IN = ["PDF", "DOCX", "Markdown", "ReqIF", "Excel", "CSV", "DBC", "Answer keys"];
export const HUB_OUT = ["ReqIF", "Excel", "pytest", "Robot", "CAPL", "Evidence report"];

export const WHY = [
  { title: "Works on anyone's output", text: "Requirements and tests from any tool or any person. You don't have to generate with Zyn to check with Zyn." },
  { title: "Quotes located by code", text: "An AI finding without a quote that code can locate in the source is never shown." },
  { title: "No confidence scores", text: "You see which checks raised findings, not a model's opinion of itself." },
  { title: "No silent pass", text: "Empty or junk input is refused or reported as skipped. It is never marked as without findings." },
  { title: "Decisions persist", text: "Dismiss a finding once. It stays dismissed on later runs of the same text." },
  { title: "Checks your AI assistant too", text: "Plug Zyn's checks into an AI coding assistant, so it checks its own work before it hands it to you." },
];

// "Use it when": the daily situations Zyn is for, from the README.
export const WHEN = [
  { who: "A supplier or a colleague hands you AI-written requirements", then: "See what was changed, invented or weakened before you sign." },
  { who: "You have a test suite from an AI assistant", then: "See which tests name signals that don't exist, or can never fail." },
  { who: "A specification got a new revision", then: "Get the list of approved requirements it affects." },
  { who: "You inherited a CAN database", then: "List its overlaps, impossible ranges and undeclared nodes before you build on it." },
  { who: "You are choosing a model", then: "Compare accuracy, repeatability and cost per correct answer on public data, not a vendor's slide." },
];

export const FITS = [
  { use: "DOORS Next, Polarion, Codebeamer", gets: "ReqIF files in and out, with review state and findings as attributes. Import into DOORS Next and Polarion not yet tested" },
  { use: "pytest, Robot Framework, CANoe", gets: "Test stubs in each format to map in your tool, plus a flat step table" },
  { use: "CI and test benches", gets: "zyn remote with an access token, against a team server" },
  { use: "An AI coding agent", gets: "An MCP server: the agent calls Zyn's checks inside its own loop" },
  { use: "Assessors", gets: "An evidence report and an ISO/IEC 33020 style checklist per run" },
];

// Personal mode and team mode: the same install, the same checks. From the README table.
export const MODES = [
  { id: "desk", label: "On your desk", cmd: "zyn serve", note: "Personal mode" },
  { id: "team", label: "For your team", cmd: "zyn serve --team", note: "Team mode" },
] as const;

export const MODE_ROWS: { k: string; desk: string; team: string }[] = [
  { k: "runs on", desk: "your own computer", team: "your network or cloud account" },
  { k: "you are", desk: "a name you type", team: "your company sign-in" },
  { k: "record", desk: "a file on your PC", team: "shared database where the running app can only add records" },
  { k: "roles", desk: "you", team: "viewer, engineer, approver" },
  { k: "programmes", desk: "one", team: "kept apart, per sign-in group" },
  { k: "approvals", desk: "yours", team: "four eyes: never your own work" },
  { k: "test benches", desk: "the command line", team: "tokens that can never approve" },
  { k: "models", desk: "Claude or local Ollama", team: "only those IT allows" },
];

export type RoadItem = { title: string; text: string };
export const ROAD: { status: "Built" | "Next" | "Later"; items: RoadItem[] }[] = [
  {
    status: "Built",
    items: [
      { title: "Team server", text: "Built and tested in a container, not yet run at a company. Company sign-in, roles and walls per project, four eyes, a shared append-only PostgreSQL log, access tokens for CI and test benches, and a container package. The container builds, starts and signs in through a trial Keycloak on every change." },
      { title: "Light install", text: "One wheel, the zyn command and zyn demo. No Node.js needed." },
    ],
  },
  {
    status: "Next",
    items: [
      { title: "Model connectors", text: "Built, not tried against live endpoints. An admin points Zyn at AWS Bedrock, Google Vertex, Azure or an OpenAI-style endpoint such as vLLM by configuration, and can forbid anything else." },
      { title: "Daily-workflow fit", text: "A requirement set and its review state go round trip with a requirement tool. Test reviews cover CANoe CAPL and vTESTstudio. J1939 checks for commercial vehicles join here." },
      { title: "Trust pack", text: "An engineer-reviewed answer key, a tool-qualification kit, and a security pack with architecture, data flows and a software bill of materials." },
      { title: "Swapped terms", text: "A signal or status swapped for another valid one passes every code check today. A term-level comparison against the source sentence is the next check to try." },
      { title: "Diagnostics", text: "A UDS and DTC catalogue checked against its ODX or CDD description." },
    ],
  },
  {
    status: "Later",
    items: [
      { title: "ALM connectors", text: "DOORS Next, Polarion, Codebeamer or Jama, chosen by actual use." },
      { title: "Coverage on real code", text: "Measuring what the tests reach, not only what they claim." },
      { title: "Scribe", text: "Documents." },
    ],
  },
];

export const NOT_BUILDING = [
  "Autonomous TARA or safety analysis",
  "MISRA compliance verdicts from a model",
  "Automatic baselining or approval of safety requirements",
  "RFQ-to-quotation automation",
  "Productivity percentages",
];

export const LIMITS = [
  "Prototype. Every screen and export says so.",
  "Public and synthetic data only. No company or customer documents.",
  "The ICX-100 answer key was written by Claude and checked by an AI reviewer, not an engineer.",
  "No productivity claims. No benchmark here measures time saved.",
  "Team mode is new. The container runs end to end with a trial Keycloak sign-in, but has not yet run behind a company's own sign-in or network.",
  "An advisory pre-review, not a qualified tool under ISO 26262. A draft tool confidence argument exists; a safety engineer has not reviewed it.",
];

export const FAQ = [
  { q: "Do I have to generate with Zyn to use it?", a: "No. Sift Review and Anvil Review check work from any tool or person. That is the main use." },
  { q: "Does my data leave my machine?", a: "Only if you let it. The code checks never call a model. Once you set an Anthropic key, the AI reviewer sends requirement text to Anthropic's API; run local models through Ollama instead, or set offline mode and every cloud call is refused. Zyn sends nothing to its makers." },
  { q: "What does a run with no code-check findings mean?", a: "That Zyn's code checks found nothing, not that the work is right. They miss a signal name swapped for another valid one (1 of 52 caught) and a flipped expected value (0 of 15). A person still reviews every item." },
  { q: "Can a whole team use it?", a: "Yes. Team mode runs on a server in your network or cloud account, with company sign-in, roles per programme, a shared PostgreSQL audit log and four eyes on by default." },
  { q: "Can the AI approve anything?", a: "No. The audit store refuses an approval from anything that is not a named person. Access tokens and service accounts can't approve either." },
  { q: "Why no confidence score?", a: "A model's rating of itself has not been shown to predict correctness. Zyn shows checks that raised findings or no flag, and quotes you can read." },
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
  { id: "how", label: "How it works" },
  { id: "proof", label: "Proof" },
  { id: "tools", label: "Tools" },
  { id: "teams", label: "Teams" },
  { id: "work", label: "Daily work" },
  { id: "roadmap", label: "Roadmap" },
  { id: "contribute", label: "Contribute" },
];
