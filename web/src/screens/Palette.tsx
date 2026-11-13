// Ctrl+K: jump to any run, start a new one, switch theme.

import { Command } from "cmdk";
import { Moon, Plus, Sun } from "../components/icons";
import { markFor } from "../components/ui";
import { AnimatePresence, motion } from "motion/react";
import { Dialog } from "radix-ui";
import { useRuns } from "../lib/api";
import { useReviewer } from "../lib/reviewer";
import { fade, T_BASE } from "../components/motion";
import { REVIEW_KEYS } from "../lib/keys";

export function Palette({ open, onOpenChange, onRun, onNew }: {
  open: boolean; onOpenChange: (v: boolean) => void; onRun: (id: string) => void; onNew: () => void;
}) {
  const runs = useRuns();
  const { setTheme } = useReviewer();
  const go = (fn: () => void) => { fn(); onOpenChange(false); };
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={T_BASE} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <motion.div className="palette" variants={fade} initial="hidden" animate="show" exit="exit">
                <Dialog.Title className="sr-only">Find a run or action</Dialog.Title>
                <Command label="Find a run or action">
                  <Command.Input placeholder="Find a run, a file, or an action..." autoFocus />
                  <Command.List>
                    <Command.Empty>Nothing matches.</Command.Empty>
                    <Command.Group heading="Actions">
                      <Command.Item onSelect={() => go(onNew)}><Plus />Start new run</Command.Item>
                      <Command.Item onSelect={() => go(() => setTheme("light"))}><Sun />Light theme</Command.Item>
                      <Command.Item onSelect={() => go(() => setTheme("dark"))}><Moon />Dark theme</Command.Item>
                    </Command.Group>
                    <Command.Group heading="Runs">
                      {(runs.data ?? []).map((r) => {
                        const Icon = markFor(r.tool);
                        return (
                          <Command.Item key={r.run_id} value={`${r.tool} ${r.note} ${r.run_id}`}
                            onSelect={() => go(() => onRun(r.run_id))}>
                            <Icon /><span className="grow">{r.tool} · {r.note || r.run_id}</span>
                            <code className="small quiet">{r.run_id.slice(9, 15)}</code>
                          </Command.Item>
                        );
                      })}
                    </Command.Group>
                    <Command.Group heading="Keyboard">
                      {REVIEW_KEYS.map(([k, what]) => (
                        <Command.Item key={k} value={`key ${k} ${what}`} onSelect={() => onOpenChange(false)}>
                          <span className="kbd">{k}</span><span className="grow">{what}</span>
                        </Command.Item>
                      ))}
                    </Command.Group>
                  </Command.List>
                </Command>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
