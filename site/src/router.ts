import { useEffect, useState } from "react";
import { BASE, HOME } from "./docs/docs";

// A tiny router. Pages are "" (home) or a docs slug. Each docs page also exists as its own
// folder with an index.html at build time (scripts/pages.mjs), so a direct visit or a refresh works.

export const pageOf = (pathname: string) => {
  if (pathname === HOME) return ""; // "/zyn" without the slash is the home page too
  const rest = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname.replace(/^\//, "");
  return rest.replace(/\/+$/, "").replace(/\.html$/, "").replace(/\/index$/, "");
};

export function scrollToHash(hash: string, immediate = false) {
  const el = hash ? document.getElementById(decodeURIComponent(hash.slice(1))) : null;
  if (!el) return false;
  const top = el.getBoundingClientRect().top + window.scrollY - 24;
  window.scrollTo({ top, behavior: immediate ? ("instant" as ScrollBehavior) : "smooth" });
  return true;
}

export function navigate(href: string) {
  const url = new URL(href, window.location.href);
  const samePage = pageOf(url.pathname) === pageOf(window.location.pathname);
  if (samePage && url.hash) {
    history.pushState(null, "", url.pathname + url.hash);
    scrollToHash(url.hash);
    return;
  }
  history.pushState(null, "", url.pathname + url.hash);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function usePage() {
  const [page, setPage] = useState(() => pageOf(window.location.pathname));
  useEffect(() => {
    const onPop = () => setPage(pageOf(window.location.pathname));
    window.addEventListener("popstate", onPop);
    // Internal links anywhere on the page (including rendered markdown) go through the router.
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element).closest?.("a");
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      const url = new URL(a.href, window.location.href);
      if (url.origin !== window.location.origin || !(url.pathname === HOME || url.pathname.startsWith(BASE))) return;
      if (url.pathname.startsWith(`${BASE}demo`)) return; // the online demo is its own app: a normal page load
      e.preventDefault();
      navigate(url.href);
    };
    document.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("popstate", onPop);
      document.removeEventListener("click", onClick);
    };
  }, []);
  return page;
}

/** Go to a home-page section from anywhere. */
export function goSection(id: string) {
  if (pageOf(window.location.pathname) === "") {
    history.replaceState(null, "", `${HOME}#${id}`);
    scrollToHash(`#${id}`);
  } else {
    navigate(`${HOME}#${id}`);
  }
}
