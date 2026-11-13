// Reviewer name and theme, kept in the browser so a reload keeps them.

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type Theme = "system" | "light" | "dark";
interface Ctx {
  reviewer: string; setReviewer: (v: string) => void;
  theme: Theme; setTheme: (t: Theme) => void;
}
const C = createContext<Ctx>({ reviewer: "", setReviewer: () => {}, theme: "system", setTheme: () => {} });

const read = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } };

export function ReviewerProvider({ children }: { children: ReactNode }) {
  const [reviewer, setR] = useState(() => read("zyn.reviewer", ""));
  const [theme, setT] = useState<Theme>(() => read("zyn.theme", "system") as Theme);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && mq.matches);
      document.documentElement.dataset.theme = dark ? "dark" : "light";
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);

  // Stable value: cards re-render only when the name or theme actually changes.
  const value = useMemo<Ctx>(() => ({
    reviewer: reviewer.trim(),
    setReviewer: (v) => { setR(v); write("zyn.reviewer", v); },
    theme, setTheme: (t) => { setT(t); write("zyn.theme", t); },
  }), [reviewer, theme]);
  return <C.Provider value={value}>{children}</C.Provider>;
}

export const useReviewer = () => useContext(C);
