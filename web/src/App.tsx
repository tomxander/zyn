import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { ApiError, useConfig, useRun, useRuns } from "./lib/api";
import { Button, Empty, Msg, Skeleton } from "./components/ui";
import { Loading } from "./components/Loader";
import { fade } from "./components/motion";
import { useReviewKeys } from "./lib/keys";
import { useReviewer } from "./lib/reviewer";
import { RotateCw } from "./components/icons";
import { Boundary } from "./components/Boundary";
import { Shell } from "./screens/Shell";
import { Palette } from "./screens/Palette";
import { NewRun } from "./screens/NewRun";
import { JobsStrip } from "./screens/JobsStrip";
import { SiftView } from "./screens/SiftView";
import { SmokeView } from "./screens/SmokeView";
import { CheckView } from "./screens/CheckView";
import { AnvilView } from "./screens/AnvilView";
import { DeltaView } from "./screens/DeltaView";
import { SignIn } from "./screens/SignIn";
import { TokensDrawer } from "./screens/Tokens";
import { TeamSettingsDrawer } from "./screens/TeamSettings";

const VIEWS: Record<string, (p: { data: any }) => JSX.Element> = {
  sift: SiftView, smoke: SmokeView, check: CheckView, forge: AnvilView, delta: DeltaView,
};

const fromUrl = () => new URLSearchParams(location.search).get("run");

/** Opening a run: the shape of the page, with a slow sweep, while the view loads. */
function RunSkeleton() {
  return (
    <div className="stack-lg" aria-busy="true">
      <Loading label="Opening the run" />
      <Skeleton height={64} />
      {[0, 1, 2].map((i) => <Skeleton key={i} height={168} />)}
    </div>
  );
}

export default function App() {
  useReviewKeys();
  const cfg = useConfig();
  const runs = useRuns();
  const { canAct } = useReviewer();
  const [runId, setRunId] = useState<string | null>(fromUrl);
  const [palette, setPalette] = useState(false);
  const [newRun, setNewRun] = useState(false);
  const [tokensOpen, setTokensOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const run = useRun(runId);

  useEffect(() => {
    if (!runId && runs.data?.length) setRunId(runs.data[0].run_id);
  }, [runs.data, runId]);
  useEffect(() => {
    if (!runId) return;
    const u = new URL(location.href);
    u.searchParams.set("run", runId);
    history.replaceState(null, "", u);
  }, [runId]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((v) => !v); }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);

  const is401 =
    (cfg.error instanceof ApiError && cfg.error.status === 401) ||
    (runs.error instanceof ApiError && runs.error.status === 401) ||
    (run.error instanceof ApiError && run.error.status === 401) ||
    (cfg.data?.mode === "team" && !cfg.data?.person);

  if (is401) {
    return <SignIn />;
  }

  const View = run.data ? VIEWS[run.data.kind] : null;
  return (
    <Shell
      runId={runId}
      onRun={setRunId}
      onNew={() => setNewRun(true)}
      onPalette={() => setPalette(true)}
      onOpenTokens={() => setTokensOpen(true)}
      onOpenSettings={() => setSettingsOpen(true)}
    >
      <JobsStrip jobKey="new" onDone={(r) => r?.run_id && setRunId(r.run_id)} />
      {runs.isError ? (
        <div className="stack">
          <Msg tone="bad">The list of runs could not be read: {(runs.error as Error).message}</Msg>
          <div><Button icon={RotateCw} onClick={() => runs.refetch()}>Try again</Button></div>
        </div>
      ) : runs.data && !runs.data.length ? (
        <Empty
          title="No runs yet"
          body={canAct ? "Start one with Start new run in the sidebar." : cfg.data?.mode === "team" ? "No runs in this project yet." : "Enter your name under Reviewer, then use Start new run."}
        />
      ) : run.isError ? (
        <div className="stack">
          <Msg tone="bad">{(run.error as Error).message}</Msg>
          <div><Button icon={RotateCw} onClick={() => run.refetch()}>Try again</Button></div>
        </div>
      ) : !run.data || !View ? (
        <RunSkeleton />
      ) : (
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div key={runId} variants={fade} initial="hidden" animate="show" exit="exit">
            <Boundary what="This run" resetKey={runId}><View data={run.data} /></Boundary>
          </motion.div>
        </AnimatePresence>
      )}
      <Palette open={palette} onOpenChange={setPalette} onRun={setRunId} onNew={() => setNewRun(true)} />
      <NewRun open={newRun} onOpenChange={setNewRun} onStarted={(id) => id && setRunId(id)} />
      <Boundary what="Access tokens"><TokensDrawer open={tokensOpen} onOpenChange={setTokensOpen} /></Boundary>
      <Boundary what="Team settings"><TeamSettingsDrawer open={settingsOpen} onOpenChange={setSettingsOpen} /></Boundary>
    </Shell>
  );
}
