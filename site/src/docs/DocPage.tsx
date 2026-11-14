import { useEffect, useMemo, useState } from "react";
import { Headline, Icon, Tag } from "../components/ui";
import { DOCS, type DocMeta, docHref, splitDoc } from "./docs";
import { Markdown, useDoc } from "./Markdown";

const TOOL_MARK: Record<string, string> = {
  sift: "sift",
  "sift-review": "sift",
  "sift-delta": "sift",
  anvil: "anvil",
  "anvil-review": "anvil",
  assay: "assay",
};

export function DocPage({ meta }: { meta: DocMeta }) {
  const { title, lede, body } = useMemo(() => splitDoc(meta.file), [meta.file]);
  const { tokens, headings } = useDoc(body);
  const toc = headings.filter((h) => h.depth === 2);
  const active = useActiveHeading(toc.map((h) => h.id));
  const i = DOCS.findIndex((d) => d.slug === meta.slug);
  const prev = i > 0 ? DOCS[i - 1] : null;
  const next = i < DOCS.length - 1 ? DOCS[i + 1] : null;

  useEffect(() => {
    document.title = meta.slug === "docs" ? "Zyn docs" : `${title}: Zyn docs`;
  }, [meta.slug, title]);

  return (
    <article className="doc" aria-labelledby="doc-title">
      <header className="doc__head field field--hero">
        <div className="wrap doc__head-in">
          <nav className="crumbs" aria-label="Breadcrumb">
            <a href={docHref("docs")}>Docs</a>
            <span aria-hidden>/</span>
            <span>{meta.group}</span>
          </nav>
          <div className="doc__title-row">
            {TOOL_MARK[meta.slug] && <Icon name={TOOL_MARK[meta.slug]} size={44} className="doc__mark" />}
            <Headline as="h1" id="doc-title" className="headline--doc" plain={title} inked={meta.inked} />
          </div>
          {lede && <p className="lead doc__lede" dangerouslySetInnerHTML={{ __html: inlineLede(lede) }} />}
        </div>
      </header>

      <div className="wrap doc__grid">
        {toc.length > 1 ? (
          <aside className="toc" aria-label="On this page">
            <Tag>On this page</Tag>
            <ol>
              {toc.map((h) => (
                <li key={h.id}>
                  <a href={`#${h.id}`} aria-current={active === h.id ? "location" : undefined}>
                    {h.text}
                  </a>
                </li>
              ))}
            </ol>
          </aside>
        ) : (
          <div />
        )}
        <div className="doc__body">
          <Markdown tokens={tokens} />
          <p className="doc__source">
            From the Zyn wiki page <code>{meta.file}.md</code>. Zyn prototype: public and synthetic data only.
          </p>
          <nav className="pager" aria-label="More pages">
            {prev ? (
              <a className="pager__link" href={docHref(prev.slug)}>
                <span className="pager__dir">Previous</span>
                <span className="pager__name">{nameOf(prev)}</span>
              </a>
            ) : (
              <span />
            )}
            {next && (
              <a className="pager__link pager__link--next" href={docHref(next.slug)}>
                <span className="pager__dir">Next</span>
                <span className="pager__name">{nameOf(next)}</span>
              </a>
            )}
          </nav>
        </div>
      </div>
    </article>
  );
}

const nameOf = (d: DocMeta) => (d.slug === "docs" ? "All docs" : splitDoc(d.file).title);

// The lede is one paragraph of inline markdown; render bold, code and links simply.
function inlineLede(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\(([A-Za-z0-9-]+)\.md\)/g, (_m, t, f) => {
      const d = DOCS.find((x) => x.file === f);
      return d ? `<a href="${docHref(d.slug)}">${t}</a>` : t;
    })
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
}

function useActiveHeading(ids: string[]) {
  const [active, setActive] = useState<string | undefined>(ids[0]);
  useEffect(() => {
    const els = ids.map((id) => document.getElementById(id)).filter(Boolean) as HTMLElement[];
    if (!els.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-90px 0px -65% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [ids.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps
  return active;
}
