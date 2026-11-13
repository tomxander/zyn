// Icons: Zyn's own identity set only (zyn-identity/, drawn on a 4 x 4 grid: one route, one
// review gap on the tool marks, one square signal dot). Screens import every icon from here.
// A meaning the set lacks gets a new glyph in zyn-identity/tools/build.py, never a stock icon.
//
// The sprite is a copy of zyn-identity/icons/zyn-sprite.svg; rebuild it there and copy it over.

import { forwardRef, type ComponentType, type SVGProps } from "react";
import sprite from "../assets/zyn-sprite.svg?raw";

type IconProps = SVGProps<SVGSVGElement> & { size?: number | string };
/** Any icon component from this file. */
export type ZynIconType = ComponentType<IconProps>;

/** Mount once: the symbols every Zyn icon points at. */
export const ZynSprite = () => (
  <div aria-hidden style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}
    dangerouslySetInnerHTML={{ __html: sprite }} />
);

function zyn(id: string, name: string) {
  const C = forwardRef<SVGSVGElement, IconProps>(function ZynIcon({ size = 24, ...rest }, ref) {
    return (
      <svg ref={ref} viewBox="0 0 24 24" width={size} height={size} focusable="false"
        aria-hidden={rest["aria-label"] ? undefined : true} className="zyn-icon" {...rest}>
        <use href={`#zyn-${id}`} />
      </svg>
    );
  });
  C.displayName = name;
  return C;
}

/** The Zyn mark: a Z traced as one route, its review gap on the diagonal, the signal dot at the end. */
export const ZynMark = forwardRef<SVGSVGElement, IconProps>(function ZynMark({ size = 24, ...rest }, ref) {
  return (
    <svg ref={ref} viewBox="0 0 24 24" width={size} height={size} focusable="false" className="zyn-icon" {...rest}>
      <path d="M3 3 L21 3 L3 21 L21 21" fill="none" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="square" strokeLinejoin="miter" strokeDasharray="26.97792206 7.5 1000 1000" />
      <rect className="zyn-dot" x="20" y="20" width="2" height="2" />
    </svg>
  );
});

// Tool marks
export const Sift = zyn("sift", "Sift");
export const Anvil = zyn("anvil", "Anvil");
export const Scribe = zyn("scribe", "Scribe");
export const Source = zyn("source", "Source");
export const Assay = zyn("assay", "Assay");

// Generic names the screens already use, drawn from the identity set
export const Check = zyn("approve", "Check");
export const X = zyn("reject", "X");
export const Search = zyn("search", "Search");
export const Plus = zyn("new-run", "Plus");
export const FileDown = zyn("export", "FileDown");
export const Download = zyn("export", "Download");
export const ScanText = Sift;
export const FileSearch = zyn("code-check", "FileSearch");
export const FlaskConical = Anvil;
export const GitCompare = zyn("compare", "GitCompare");
export const FileDiff = zyn("compare", "FileDiff");
export const FileCheck = zyn("evidence-report", "FileCheck");
export const TriangleAlert = zyn("warning", "TriangleAlert");
export const AlertTriangle = TriangleAlert;
export const Info = zyn("info", "Info");
export const CircleAlert = zyn("needs-review", "CircleAlert");
export const CircleCheck = zyn("passed", "CircleCheck");
export const Blocked = zyn("blocked", "Blocked");
export const ListChecks = zyn("empty", "ListChecks");
export const RotateCcw = zyn("send-back", "RotateCcw");
export const RotateCw = zyn("run-again", "RotateCw");
export const RefreshCw = zyn("run-again", "RefreshCw");
export const Repeat = zyn("replay", "Repeat");
export const Cog = zyn("settings", "Cog");
export const Layers = zyn("rule-profiles", "Layers");
export const Person = zyn("person", "Person");
export const AiReviewer = zyn("ai-reviewer", "AiReviewer");
export const Running = zyn("running", "Running");

// Added to the identity set for the review screen
export const Pencil = zyn("edit", "Pencil");
export const Sparkles = zyn("propose", "Sparkles");
export const Wand2 = zyn("apply", "Wand2");
export const WandSparkles = Wand2;
export const CheckCheck = zyn("approve-all", "CheckCheck");
export const ArrowRight = zyn("next", "ArrowRight");
export const Monitor = zyn("theme-system", "Monitor");
export const Sun = zyn("theme-light", "Sun");
export const Moon = zyn("theme-dark", "Moon");
export const Command = zyn("key", "Command");
export const ChevronDown = zyn("chevron-down", "ChevronDown");
export const ChevronRight = zyn("chevron-right", "ChevronRight");
export const Save = zyn("save", "Save");
export const Target = zyn("score", "Target");
export const Upload = zyn("open-file", "Upload");
