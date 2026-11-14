import type { ReactNode } from "react";
import { type Pattern, PatternField } from "./PatternField";

/** A section panel: the section's field colour, live line art, ink bars top and bottom,
 *  a 1 px ink frame above everything, and the content card in the middle. */
export function Panel({
  sa,
  pattern,
  className = "",
  children,
}: {
  sa: number;
  pattern: Pattern;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`panel field--sa ${className}`} data-sa={sa}>
      <PatternField pattern={pattern} />
      <span className="panel__bar panel__bar--top" aria-hidden />
      <span className="panel__bar panel__bar--bottom" aria-hidden />
      <div className="panel__content">{children}</div>
    </div>
  );
}
