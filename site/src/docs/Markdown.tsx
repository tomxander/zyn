import { Marked, type Token, type Tokens } from "marked";
import { Fragment, type ReactNode, useMemo } from "react";
import { CopyGlyph, copyText } from "../components/ui";
import { rewriteLink, slugify } from "./docs";
import { Flow } from "./Flow";

// Inline markdown (bold, code, links) goes through marked; links are rewritten so wiki pages
// open as site pages and repository files show as plain paths (the repository is private).
const inline = new Marked({
  renderer: {
    link({ href, tokens }) {
      const text = this.parser.parseInline(tokens);
      const r = rewriteLink(href);
      if (r.kind === "repo") return `<code class="md-path" title="In the Zyn repository">${r.href}</code>`;
      // Coming soon: no links off the site yet, so outside addresses show as plain text.
      if (r.kind === "external") return `<span class="md-ext">${text}</span>`;
      return `<a href="${r.href}"${r.kind === "doc" ? " data-internal" : ""}>${text}</a>`;
    },
  },
});

const html = (s: string) => inline.parseInline(s, { async: false }) as string;
const Html = ({ s, as: Tag = "span" }: { s: string; as?: "span" | "p" | "div" }) => (
  <Tag dangerouslySetInnerHTML={{ __html: html(s) }} />
);

export type Heading = { id: string; text: string; depth: number };

export function useDoc(body: string) {
  return useMemo(() => {
    const tokens = new Marked().lexer(body);
    const headings: Heading[] = tokens
      .filter((t): t is Tokens.Heading => t.type === "heading" && t.depth <= 3)
      .map((t) => ({ id: slugify(t.text), text: t.text.replace(/\*\*/g, ""), depth: t.depth }));
    return { tokens, headings };
  }, [body]);
}

export function Markdown({ tokens }: { tokens: Token[] }) {
  return <div className="md">{tokens.map((t, i) => <Block key={i} t={t} />)}</div>;
}

function Block({ t }: { t: Token }): ReactNode {
  switch (t.type) {
    case "heading": {
      const h = t as Tokens.Heading;
      const id = slugify(h.text);
      const Tag = (`h${Math.min(4, h.depth + 0)}` as "h2" | "h3" | "h4");
      return (
        <Tag id={id} className={`md-h md-h${h.depth}`}>
          <a href={`#${id}`} className="md-anchor" aria-hidden tabIndex={-1}>
            #
          </a>
          <Html s={h.text} />
        </Tag>
      );
    }
    case "paragraph":
      return <Html as="p" s={(t as Tokens.Paragraph).text} />;
    case "list": {
      const l = t as Tokens.List;
      const Tag = l.ordered ? "ol" : "ul";
      return (
        <Tag className={`md-list ${l.ordered ? "md-list--ol" : ""}`}>
          {l.items.map((it, i) => (
            <li key={i}>
              {l.ordered && <span className="md-num">{String(i + 1).padStart(2, "0")}</span>}
              <span className="md-li">
                {it.tokens.map((c, j) =>
                  c.type === "text" ? <Html key={j} s={(c as Tokens.Text).text} /> : <Block key={j} t={c} />,
                )}
              </span>
            </li>
          ))}
        </Tag>
      );
    }
    case "table": {
      const tb = t as Tokens.Table;
      return (
        <div className="md-table" role="region" tabIndex={0} aria-label="Table">
          <table>
            <thead>
              <tr>
                {tb.header.map((h, i) => (
                  <th key={i} style={{ textAlign: tb.align[i] ?? undefined }}>
                    <Html s={h.text} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tb.rows.map((r, i) => (
                <tr key={i}>
                  {r.map((c, j) => (
                    <td key={j} style={{ textAlign: tb.align[j] ?? undefined }}>
                      <Html s={c.text} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    case "code": {
      const c = t as Tokens.Code;
      if (c.lang === "mermaid") return <Flow source={c.text} />;
      return <Code text={c.text} lang={c.lang} />;
    }
    case "blockquote":
      return (
        <blockquote className="md-quote">
          {(t as Tokens.Blockquote).tokens.map((c, i) => <Block key={i} t={c} />)}
        </blockquote>
      );
    case "hr":
      return <hr className="md-hr" />;
    case "html":
      return <Html as="div" s={(t as Tokens.HTML).text} />;
    case "text":
      return <Html as="p" s={(t as Tokens.Text).text} />;
    case "space":
      return null;
    default:
      return <Fragment />;
  }
}

function Code({ text, lang }: { text: string; lang?: string }) {
  const label = lang === "powershell" ? "PowerShell" : lang || "Text";
  return (
    <figure className="md-code">
      <figcaption>
        <span>{label}</span>
        <button type="button" onClick={() => copyText(text)} aria-label="Copy this block">
          <CopyGlyph />
        </button>
      </figcaption>
      <pre>
        {text.split("\n").map((line, i) => {
          const hash = line.indexOf("#");
          const isCmd = lang === "powershell" || lang === "bash";
          if (isCmd && hash > 0) {
            return (
              <span key={i} className="md-code__line">
                {line.slice(0, hash)}
                <span className="md-code__comment">{line.slice(hash)}</span>
                {"\n"}
              </span>
            );
          }
          return (
            <span key={i} className={`md-code__line ${isCmd && line.startsWith("#") ? "md-code__comment" : ""}`}>
              {line}
              {"\n"}
            </span>
          );
        })}
      </pre>
    </figure>
  );
}
