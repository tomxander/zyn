// Keyboard review: j / k move between cards, a approves, r rejects, e opens edit.
// Cards carry data-card; their buttons carry data-key. Keys are ignored while typing or
// while a drawer or the palette is open.

import { useEffect } from "react";
import { announce } from "./api";
import { MS_ADVANCE } from "../components/motion";

export const REVIEW_KEYS: [string, string][] = [
  ["j", "Next card"], ["k", "Previous card"], ["a", "Approve, confirm or needs action"],
  ["r", "Reject, dismiss or no action"], ["e", "Edit the card"], [/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘ K" : "Ctrl K", "Find a run or action"],
  ["Ctrl Enter", "Save in an open drawer"],
];

let lastIndex = -1;

const cards = () => [...document.querySelectorAll<HTMLElement>("[data-card]")];
const current = () => document.querySelector<HTMLElement>("[data-card][data-current]");

function mark(card: HTMLElement) {
  current()?.removeAttribute("data-current");
  card.setAttribute("data-current", "");
  lastIndex = cards().indexOf(card);
}

/** Move the current mark from one card to the next or previous one. */
function step(from: HTMLElement | null, dir: 1 | -1) {
  const all = cards();
  if (!all.length) return;
  let i = from && all.includes(from) ? all.indexOf(from) : Math.min(lastIndex, all.length - 1);
  i = Math.max(0, Math.min(i + dir, all.length - 1));
  const next = all[i];
  mark(next);
  next.focus({ preventScroll: true });
  const smooth = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  next.scrollIntoView({ block: "nearest", behavior: smooth ? "smooth" : "auto" });
}

function typing(t: EventTarget | null) {
  const el = t as HTMLElement | null;
  return !!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName));
}

export function useReviewKeys() {
  useEffect(() => {
    const onFocus = (e: FocusEvent) => {
      const card = (e.target as HTMLElement | null)?.closest?.("[data-card]") as HTMLElement | null;
      if (card) mark(card);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target)) return;
      if (document.querySelector('[role="dialog"]')) return;
      const k = e.key.toLowerCase();
      if (k === "j" || k === "k") {
        if (!cards().length) return;
        step(current(), k === "j" ? 1 : -1);
        e.preventDefault();
      } else if (k === "a" || k === "r" || k === "e") {
        const card = current();
        const btn = card?.querySelector<HTMLButtonElement>(`[data-key="${k}"]`);
        if (!card || !btn) return;
        e.preventDefault();
        if (btn.disabled || btn.getAttribute("aria-disabled") === "true") {
          announce(`${btn.textContent?.trim()} is not available here`);
          return;
        }
        btn.click();
        // A decision by key moves on to the next sheet, unless a reason must be chosen first.
        // (An optional reason picker, such as "Reason, if dismissing", does not stop it.)
        if ((k === "a" || k === "r") && !card.querySelector("[data-reason-required]")) {
          setTimeout(() => step(card, +1), MS_ADVANCE);
        }
      }
    };
    document.addEventListener("focusin", onFocus);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("focusin", onFocus);
      document.removeEventListener("keydown", onKey);
    };
  }, []);
}
