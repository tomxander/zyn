// Reviewer name and theme, kept in the browser so a reload keeps them.

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useConfig } from "./api";

type Theme = "system" | "light" | "dark";
interface Ctx {
  reviewer: string;
  setReviewer: (v: string) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  canAct: boolean;
  noActReason?: string;
}
const C = createContext<Ctx>({
  reviewer: "",
  setReviewer: () => {},
  theme: "system",
  setTheme: () => {},
  canAct: false,
  noActReason: undefined,
});

const read = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const write = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } };

export function ReviewerProvider({ children }: { children: ReactNode }) {
  const [storedReviewer, setR] = useState(() => read("zyn.reviewer", ""));
  const [theme, setT] = useState<Theme>(() => read("zyn.theme", "system") as Theme);
  const cfg = useConfig();

  const isTeam = cfg.data?.mode === "team";
  const reviewer = (isTeam ? cfg.data?.person?.name : storedReviewer) || "";

  let canAct = false;
  let noActReason: string | undefined = undefined;

  if (isTeam) {
    if (!cfg.data?.person) {
      canAct = false;
      noActReason = "Sign in first";
    } else {
      const activeProjId = cfg.data.project;
      const proj = cfg.data.projects?.find((p: any) => p.id === activeProjId);
      const role = proj?.role;
      if (role === "engineer" || role === "approver") {
        canAct = true;
      } else if (role === "viewer") {
        canAct = false;
        noActReason = "Your role on this project is viewer; editing and starting runs are not allowed.";
      } else {
        canAct = false;
        noActReason = "You do not have a role on this project; only viewing is allowed.";
      }
    }
  } else {
    canAct = Boolean(storedReviewer.trim());
    noActReason = canAct ? undefined : "Enter your name as reviewer first";
  }

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

  // Stable value: cards re-render only when the name, theme, or canAct changes.
  const value = useMemo<Ctx>(() => ({
    reviewer: reviewer.trim(),
    setReviewer: (v) => { setR(v); write("zyn.reviewer", v); },
    theme, setTheme: (t) => { setT(t); write("zyn.theme", t); },
    canAct,
    noActReason,
  }), [reviewer, theme, canAct, noActReason]);
  return <C.Provider value={value}>{children}</C.Provider>;
}

export const useReviewer = () => useContext(C);
