import { type ReactNode, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import sprite from "../assets/zyn-sprite.svg?raw";

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** The Zyn identity sprite, injected once. Every icon on the page comes from it. */
export function Sprite() {
  return <div hidden aria-hidden dangerouslySetInnerHTML={{ __html: sprite }} />;
}

export function Icon({ name, size = 20, className, label }: { name: string; size?: number; className?: string; label?: string }) {
  return (
    <svg
      className={`icon ${className ?? ""}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <use href={`#zyn-${name}`} />
    </svg>
  );
}

/** The Zyn Z mark, drawn as its own path so its route can be animated. */
export function ZMark({ size = 28, loop = false }: { size?: number; loop?: boolean }) {
  return (
    <svg className={`zmark ${loop ? "zmark--loop" : ""}`} width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <path
        d="M3 3 L21 3 L3 21 L21 21"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
        strokeDasharray="26.97792206 7.5 1000 1000"
      />
      <rect x="20" y="20" width="2" height="2" fill="var(--accent)" />
    </svg>
  );
}

/** Section tag: a small ink slip naming the section, a pixel hanging off its corner. */
export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="tag">
      <span className="tag__text">{children}</span>
    </span>
  );
}

/** The row that opens every section: the tag at the left, an ink plug at the right. */
export function SectionHead({ children }: { children: ReactNode }) {
  return (
    <div className="sechead">
      <Tag>{children}</Tag>
      <span className="sechead__plug" aria-hidden />
    </div>
  );
}

/** Pixel corner squares: the registration marks that frame a stage. */
export function Corners() {
  return (
    <>
      <span className="corner corner--tl" aria-hidden />
      <span className="corner corner--tr" aria-hidden />
      <span className="corner corner--bl" aria-hidden />
      <span className="corner corner--br" aria-hidden />
    </>
  );
}

/**
 * A two-line headline: the plain line, then the claim as an indented ink bar in the section's
 * accent, with a separate ink block after it. Static: the motion lives in the panels.
 */
export function Headline({
  as: Tag = "h2",
  plain,
  inked,
  className,
  id,
}: {
  as?: "h1" | "h2";
  plain: string;
  inked: string;
  className?: string;
  id?: string;
}) {
  return (
    <Tag id={id} className={`headline ${className ?? ""}`}>
      <span className="headline__plain">{plain}</span>
      <span className="inked">
        <span className="inked__fill">{inked}</span>
        <span className="inked__block" aria-hidden />
      </span>
    </Tag>
  );
}

export async function copyText(text: string, what = "Command") {
  try {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Older browsers, or a page without clipboard permission: copy through a hidden field.
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.cssText = "position:fixed;opacity:0;pointer-events:none";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      area.remove();
      if (!ok) throw new Error("copy refused");
    }
    toast(`${what} copied`, { description: text.length > 64 ? `${text.slice(0, 64)}...` : text });
  } catch {
    toast.error("Could not copy. Select the text and copy it by hand.");
  }
}

/** A command on one ruled line, with a copy button. */
export function CommandLine({ command, label = "PowerShell", tone = "ink" }: { command: string; label?: string; tone?: "ink" | "paper" }) {
  return (
    <div className={`cmd cmd--${tone}`}>
      <span className="cmd__label">
        <Icon name="key" size={14} />
        {label}
      </span>
      <code className="cmd__text" title={command}>
        {command}
      </code>
      <button type="button" className="cmd__copy" onClick={() => copyText(command)} aria-label={`Copy: ${command}`}>
        <CopyGlyph />
      </button>
    </div>
  );
}

/** Two offset squares, drawn in the identity's square-cap line. */
export function CopyGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
      <path d="M5.5 5.5h8v8h-8z M2.5 10.5v-8h8" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="square" />
    </svg>
  );
}

/** True once the element has been on screen. Used to start counters. */
export function useSeen<T extends Element>(margin = "-10% 0px") {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [margin]);
  return [ref, seen] as const;
}

/** A row of hatching across the page: the site's section break (hatch means "look here"). */
export function HatchBand({ flip = false }: { flip?: boolean }) {
  return <div className={`hatchband ${flip ? "hatchband--flip" : ""}`} aria-hidden />;
}
