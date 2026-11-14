// After `vite build`: give every docs page its own folder with an index.html, so
// thomasalex.in/zyn/sift (or a refresh on it) is served directly by any static host.
// Each copy carries its own <title> and description; the app then renders the page.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "dist");
const wiki = join(here, "..", "..", "docs", "wiki");
const docsTs = readFileSync(join(here, "..", "src", "docs", "docs.ts"), "utf8");
const shell = readFileSync(join(dist, "index.html"), "utf8");

const esc = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const plain = (s) => s.replace(/\*\*|`/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

const pages = [...docsTs.matchAll(/file: "([^"]+)", slug: "([^"]+)"/g)].map((m) => ({ file: m[1], slug: m[2] }));
for (const { file, slug } of pages) {
  const md = readFileSync(join(wiki, `${file}.md`), "utf8").replace(/\r\n/g, "\n");
  const title = file === "Home" ? "Zyn docs" : (md.match(/^# (.+)$/m)?.[1] ?? file);
  const lede = md.split("\n\n").slice(1).find((p) => p && !/^[#`|>*-]/.test(p.trim())) ?? "";
  const desc = plain(lede).replace(/\s+/g, " ").trim().slice(0, 180);
  const html = shell
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}: Zyn docs</title>`)
    .replace(/<meta name="description" content="[^"]*"/, `<meta name="description" content="${esc(desc)}"`);
  mkdirSync(join(dist, slug), { recursive: true });
  writeFileSync(join(dist, slug, "index.html"), html);
}
console.log(`docs pages written: ${pages.length}`);
