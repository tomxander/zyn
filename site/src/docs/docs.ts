// The docs pages are the repository wiki (docs/wiki/*.md), read at build time. Edit the wiki,
// rebuild the site, and the pages follow. Only the group and the inked line below live here.

const RAW = import.meta.glob("../../../docs/wiki/*.md", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

export type DocMeta = { file: string; slug: string; group: string; inked: string };

// Order here is the order of the docs index and of the previous / next links.
export const DOCS: DocMeta[] = [
  { file: "Getting-started", slug: "getting-started", group: "Use", inked: "Running in minutes." },
  { file: "How-Zyn-decides", slug: "how-zyn-decides", group: "Use", inked: "Four steps, all recorded." },
  { file: "Benchmarks", slug: "benchmarks", group: "Evidence", inked: "Every number, with its method." },
  { file: "Sift", slug: "sift", group: "Tools", inked: "Requirements with their source words." },
  { file: "Sift-Review", slug: "sift-review", group: "Tools", inked: "Check a set you already have." },
  { file: "Sift-Delta", slug: "sift-delta", group: "Tools", inked: "What a new revision changes." },
  { file: "Anvil", slug: "anvil", group: "Tools", inked: "Tests from checked templates." },
  { file: "Anvil-Review", slug: "anvil-review", group: "Tools", inked: "Check tests from any tool." },
  { file: "Assay", slug: "assay", group: "Tools", inked: "Models on public answer keys." },
  { file: "Checks-reference", slug: "checks-reference", group: "Evidence", inked: "What each check catches." },
  { file: "Research-basis", slug: "research-basis", group: "Evidence", inked: "What engineers asked for." },
  { file: "Team-server", slug: "team-server", group: "Build", inked: "One server, a whole team." },
  { file: "Integrations", slug: "integrations", group: "Build", inked: "Fits around your tools." },
  { file: "Architecture", slug: "architecture", group: "Build", inked: "The parts, and how a run flows." },
  { file: "Data-and-licences", slug: "data-and-licences", group: "Build", inked: "Public and synthetic only." },
  { file: "Development", slug: "development", group: "Build", inked: "Checks before anything is done." },
  { file: "Roadmap", slug: "roadmap", group: "Build", inked: "Next, and what is not built." },
  { file: "FAQ", slug: "faq", group: "Use", inked: "Questions people ask." },
  { file: "Home", slug: "docs", group: "Docs", inked: "Checked twice. Decided by a person." },
];

const byFile = new Map(DOCS.map((d) => [d.file, d]));
export const bySlug = new Map(DOCS.map((d) => [d.slug, d]));

export function docSource(file: string): string {
  const key = Object.keys(RAW).find((k) => k.endsWith(`/${file}.md`));
  return key ? RAW[key] : "";
}

/** Title (first H1), lede (first paragraph) and the rest of the page. */
export function splitDoc(file: string) {
  const src = docSource(file).replace(/\r\n/g, "\n");
  const lines = src.split("\n");
  const h1 = lines.findIndex((l) => l.startsWith("# "));
  const title = h1 >= 0 ? lines[h1].slice(2).trim() : file.replace(/-/g, " ");
  let rest = lines.slice(h1 + 1).join("\n").replace(/^\n+/, "");
  let lede = "";
  const para = rest.match(/^([^#\n`|>*-][^\n]*(?:\n[^\n#`|>-][^\n]*)*)\n\n/);
  if (para) {
    lede = para[1];
    rest = rest.slice(para[0].length);
  }
  return { title: file === "Home" ? "Zyn docs" : title, lede, body: rest };
}

export const BASE = import.meta.env.BASE_URL; // "/" or "/zyn/"

export const docHref = (slug: string, hash = "") => `${BASE}${slug}${hash}`;

/** Rewrite a wiki link. Wiki pages become site pages; files in the (private) repository become plain text. */
export function rewriteLink(href: string): { kind: "doc" | "external" | "repo" | "anchor"; href: string } {
  if (/^https?:\/\//.test(href)) return { kind: "external", href };
  if (href.startsWith("#")) return { kind: "anchor", href };
  const m = href.match(/^([A-Za-z0-9-]+)\.md(#.*)?$/);
  if (m && byFile.has(m[1])) return { kind: "doc", href: docHref(byFile.get(m[1])!.slug, m[2] ?? "") };
  // Wiki files sit in docs/wiki: one "../" is docs/, two is the repository root.
  const up = (href.match(/^(\.\.\/)+/)?.[0].length ?? 0) / 3;
  const path = href.replace(/^(\.\.\/)+/, "");
  return { kind: "repo", href: up === 1 ? `docs/${path}` : path };
}

export const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
