import { Fragment } from "react";

// The wiki's three diagrams are Mermaid flowcharts. Rather than ship Mermaid (about 1 MB, and
// its own look), this reads the small subset the wiki uses and draws it as ruled boxes:
// nodes with labels, solid (-->), dotted (-.->) and two-way (<-->) edges, and subgraphs.

type Node = { id: string; label: string; sub?: string; store?: boolean };
type Edge = { from: string; to: string; kind: "solid" | "dotted" | "both" };
type Group = { id: string; title: string; nodes: string[] };

const NODE = /([A-Za-z][\w]*)\s*(\[\(|\(\[|\[|\(\()"([^"]*)"\s*(\)\]|\]\)|\]|\)\))/g;

function parseLabel(raw: string) {
  const sub = raw.match(/<sub>(.*?)<\/sub>/)?.[1];
  const label = raw
    .replace(/<sub>.*?<\/sub>/, "")
    .replace(/<br\/?>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return { label, sub: sub?.replace(/<br\/?>/g, " ") };
}

export function parseFlow(src: string) {
  const nodes = new Map<string, Node>();
  const edges: Edge[] = [];
  const groups: Group[] = [];
  let dir: "LR" | "TB" = "LR";
  let current: Group | null = null;

  for (const rawLine of src.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const head = line.match(/^flowchart\s+(LR|TB|TD|RL|BT)/);
    if (head) {
      dir = head[1] === "LR" || head[1] === "RL" ? "LR" : "TB";
      continue;
    }
    const sg = line.match(/^subgraph\s+(\w+)(?:\["([^"]+)"\])?/);
    if (sg) {
      current = { id: sg[1], title: sg[2] ?? sg[1], nodes: [] };
      groups.push(current);
      continue;
    }
    if (line === "end") {
      current = null;
      continue;
    }
    // declare nodes found on the line
    for (const m of line.matchAll(NODE)) {
      const { label, sub } = parseLabel(m[3]);
      nodes.set(m[1], { id: m[1], label, sub, store: m[2] === "[(" });
      if (current && !current.nodes.includes(m[1])) current.nodes.push(m[1]);
    }
    // edges: strip node declarations, then read the chain of ids and arrows
    const bare = line.replace(NODE, "$1");
    const parts = bare.split(/\s*(<-->|-\.->|-->)\s*/);
    for (let i = 1; i < parts.length; i += 2) {
      const from = parts[i - 1].trim();
      const to = parts[i + 1]?.trim();
      if (!from || !to) continue;
      edges.push({ from, to, kind: parts[i] === "-.->" ? "dotted" : parts[i] === "<-->" ? "both" : "solid" });
    }
  }
  return { nodes, edges, groups, dir };
}

const nameOf = (id: string, nodes: Map<string, Node>, groups: Group[]) =>
  nodes.get(id)?.label ?? groups.find((g) => g.id === id)?.title ?? id;

export function Flow({ source }: { source: string }) {
  const { nodes, edges, groups } = parseFlow(source);

  // A plain chain (each solid edge continues the last) draws as numbered steps with arrows.
  const solid = edges.filter((e) => e.kind === "solid");
  const chain: string[] = [];
  if (!groups.length && solid.length) {
    chain.push(solid[0].from);
    for (const e of solid) if (e.from === chain[chain.length - 1]) chain.push(e.to);
  }
  const isChain = chain.length === solid.length + 1 && chain.length > 1;
  const extras = edges.filter((e) => e.kind !== "solid" || !isChain);

  if (isChain) {
    return (
      <figure className="diagram" aria-label="Flow diagram">
        <ol className="diagram__chain">
          {chain.map((id, i) => {
            const n = nodes.get(id);
            return (
              <Fragment key={id}>
                <li className={`diagram__node ${n?.store ? "diagram__node--store" : ""}`}>
                  <span className="diagram__step">{String(i + 1).padStart(2, "0")}</span>
                  <span className="diagram__label">{n?.label ?? id}</span>
                  {n?.sub && <span className="diagram__sub">{n.sub}</span>}
                </li>
                {i < chain.length - 1 && <li className="diagram__arrow" aria-hidden />}
              </Fragment>
            );
          })}
        </ol>
        {extras.length > 0 && (
          <figcaption className="diagram__extras">
            {extras.map((e, i) => (
              <span key={i} className="diagram__extra">
                <span className="diagram__dots" aria-hidden />
                Also recorded: {nameOf(e.from, nodes, groups)} to {nameOf(e.to, nodes, groups)}
              </span>
            ))}
          </figcaption>
        )}
      </figure>
    );
  }

  // Otherwise: groups as ruled boxes, loose nodes beside them, and the connections as a ledger.
  const grouped = new Set(groups.flatMap((g) => g.nodes));
  const loose = [...nodes.values()].filter((n) => !grouped.has(n.id));
  return (
    <figure className="diagram diagram--map" aria-label="Architecture diagram">
      <div className="diagram__groups">
        {groups.map((g) => (
          <div key={g.id} className="diagram__group">
            <span className="diagram__group-title">{g.title}</span>
            {g.nodes.map((id) => (
              <NodeBox key={id} n={nodes.get(id)!} />
            ))}
          </div>
        ))}
        {loose.length > 0 && (
          <div className="diagram__group diagram__group--loose">
            <span className="diagram__group-title">Outputs</span>
            {loose.map((n) => (
              <NodeBox key={n.id} n={n} />
            ))}
          </div>
        )}
      </div>
      <figcaption>
        <table className="diagram__edges">
          <caption>Connections</caption>
          <tbody>
            {edges.map((e, i) => (
              <tr key={i}>
                <td>{nameOf(e.from, nodes, groups)}</td>
                <td className="diagram__edge-kind" aria-label={e.kind === "both" ? "both ways" : "to"}>
                  <span className={`diagram__edge diagram__edge--${e.kind}`} />
                </td>
                <td>{nameOf(e.to, nodes, groups)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </figcaption>
    </figure>
  );
}

function NodeBox({ n }: { n: Node }) {
  return (
    <span className={`diagram__node ${n.store ? "diagram__node--store" : ""}`}>
      <span className="diagram__label">{n.label}</span>
      {n.sub && <span className="diagram__sub">{n.sub}</span>}
    </span>
  );
}
