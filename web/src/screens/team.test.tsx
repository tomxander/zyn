import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { Tooltip } from "radix-ui";
import type { ReactNode } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { DecisionBar } from "../components/Decision";
import { ReviewerProvider } from "../lib/reviewer";
import { NewRun } from "./NewRun";
import { PersonMenu } from "./PersonMenu";
import { Shell } from "./Shell";
import { SignIn } from "./SignIn";
import { TokensDrawer } from "./Tokens";
import App from "../App";

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
});

// Every Button sits in a tooltip root, as in the app (main.tsx provides it).
const TipProvider = ({ children }: { children: ReactNode }) => <Tooltip.Provider delayDuration={0}>{children}</Tooltip.Provider>;

function createTestWrapper(initialData?: { config?: any; runs?: any; tokens?: any }) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });
  if (initialData?.config) {
    qc.setQueryData(["config"], initialData.config);
  }
  if (initialData?.runs) {
    qc.setQueryData(["runs"], initialData.runs);
  }
  if (initialData?.tokens) {
    qc.setQueryData(["tokens"], initialData.tokens);
  }

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <Tooltip.Provider delayDuration={0}>
          <ReviewerProvider>{children}</ReviewerProvider>
        </Tooltip.Provider>
      </QueryClientProvider>
    );
  };
}

describe("team mode ui components", () => {
  it("renders person menu with name and role", () => {
    render(
      <PersonMenu
        person={{ name: "Alice Smith", email: "alice@example.com" }}
        projects={[{ id: "alpha", name: "Alpha", role: "approver", four_eyes: true }]}
        currentProject="alpha"
        onSelectProject={() => {}}
        onOpenTokens={() => {}}
      />,
      { wrapper: TipProvider }
    );

    expect(screen.getByText("Alice Smith")).toBeTruthy();
    expect(screen.getByText("alice@example.com")).toBeTruthy();
    expect(screen.getByText("Approver")).toBeTruthy();
  });

  it("disables decision button with four-eyes reason", () => {
    const Wrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "alice", name: "Alice" },
        roles: { generator: "auto", reviewer: "auto" },
      },
    });

    render(
      <DecisionBar
        itemId="req-1"
        decision={{
          status: "proposed",
          block_approve: null,
          block_decide: "You edited this; someone else must decide on it.",
          needs_reason: false,
          reasons: [],
          earlier: null,
        }}
      />,
      { wrapper: Wrapper }
    );

    expect(
      screen.getByText("You edited this; someone else must decide on it.")
    ).toBeTruthy();
    const approveBtn = screen.getByRole("button", { name: "Approve" });
    const isDisabled =
      approveBtn.getAttribute("aria-disabled") === "true" ||
      approveBtn.hasAttribute("disabled");
    expect(isDisabled).toBe(true);
  });

  it("renders sign-in page", () => {
    render(<SignIn />, { wrapper: TipProvider });
    expect(screen.getByText("Sign in with your company account")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Sign in with company account" })
    ).toBeTruthy();
  });

  it("shows reviewer box in personal mode", () => {
    const Wrapper = createTestWrapper({
      config: {
        mode: "personal",
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    render(
      <Shell runId={null} onRun={() => {}} onNew={() => {}} onPalette={() => {}}>
        <div>Main content</div>
      </Shell>,
      { wrapper: Wrapper }
    );

    const input = screen.getByPlaceholderText("Your name");
    expect(input).toBeTruthy();
    expect(screen.getByLabelText("Reviewer name")).toBeTruthy();
  });

  it("starts a run in team mode sending the project parameter", async () => {
    const Wrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "alice", name: "Alice" },
        project: "proj-alpha",
        projects: [{ id: "proj-alpha", name: "Project Alpha", role: "engineer", four_eyes: true }],
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ run_id: "new-run-123" }),
    } as Response);

    render(
      <NewRun open={true} onOpenChange={() => {}} onStarted={() => {}} />,
      { wrapper: Wrapper }
    );

    // Start button is disabled before selecting a file
    const startBtn = screen.getByRole("button", { name: "Start" });
    const isBtnDisabled = (btn: HTMLElement) =>
      btn.getAttribute("aria-disabled") === "true" || btn.hasAttribute("disabled");
    expect(isBtnDisabled(startBtn)).toBe(true);

    // Pick a file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(["test content"], "spec.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    // In team mode, Alice is an engineer, so startBtn is now ENABLED!
    expect(isBtnDisabled(startBtn)).toBe(false);

    // Submit
    fireEvent.click(startBtn);

    expect(fetchSpy).toHaveBeenCalled();
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain("project=proj-alpha");
    const calledInit = fetchSpy.mock.calls[0][1];
    expect(calledInit?.method).toBe("POST");
    const fd = calledInit?.body as FormData;
    expect(fd.get("project")).toBe("proj-alpha");

    fetchSpy.mockRestore();
  });

  it("keeps personal mode starting a run unchanged", async () => {
    localStorage.removeItem("zyn.reviewer");
    const Wrapper = createTestWrapper({
      config: {
        mode: "personal",
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    render(
      <NewRun open={true} onOpenChange={() => {}} onStarted={() => {}} />,
      { wrapper: Wrapper }
    );

    // Pick a file without setting a reviewer name
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(["test content"], "spec.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [testFile] } });

    // In personal mode without a reviewer name, startBtn is DISABLED!
    const startBtn = screen.getByRole("button", { name: "Start" });
    const isBtnDisabled = (btn: HTMLElement) =>
      btn.getAttribute("aria-disabled") === "true" || btn.hasAttribute("disabled");
    expect(isBtnDisabled(startBtn)).toBe(true);
  });

  it("shows hint under disabled Start new run button for viewer", () => {
    const Wrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "viewer1", name: "Viewer Dan" },
        project: "proj-alpha",
        projects: [{ id: "proj-alpha", name: "Project Alpha", role: "viewer" }],
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    render(
      <Shell runId={null} onRun={() => {}} onNew={() => {}} onPalette={() => {}}>
        <div>Main content</div>
      </Shell>,
      { wrapper: Wrapper }
    );

    const startBtn = screen.getByRole("button", { name: "Start new run" });
    const isBtnDisabled =
      startBtn.getAttribute("aria-disabled") === "true" || startBtn.hasAttribute("disabled");
    expect(isBtnDisabled).toBe(true);
    expect(
      screen.getByText("Your role on this project is viewer; editing and starting runs are not allowed.")
    ).toBeTruthy();
  });

  it("shows appropriate empty state message for viewer vs engineer", () => {
    const ViewerWrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "viewer1", name: "Viewer Dan" },
        project: "proj-alpha",
        projects: [{ id: "proj-alpha", name: "Project Alpha", role: "viewer" }],
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    const { unmount } = render(<App />, { wrapper: ViewerWrapper });
    expect(screen.getByText("No runs in this project yet.")).toBeTruthy();
    expect(screen.queryByText("Start one with Start new run in the sidebar.")).toBeNull();
    unmount();

    const EngWrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "eng1", name: "Engineer Eve" },
        project: "proj-alpha",
        projects: [{ id: "proj-alpha", name: "Project Alpha", role: "engineer" }],
        roles: { generator: "auto", reviewer: "auto" },
      },
      runs: [],
    });

    render(<App />, { wrapper: EngWrapper });
    expect(screen.getByText("Start one with Start new run in the sidebar.")).toBeTruthy();
  });

  it("shows clean copy for Tokens drawer empty state", () => {
    const Wrapper = createTestWrapper({
      config: {
        mode: "team",
        person: { id: "alice", name: "Alice" },
        project: "proj-alpha",
        projects: [{ id: "proj-alpha", name: "Project Alpha", role: "engineer" }],
      },
      tokens: [],
    });

    render(<TokensDrawer open={true} onOpenChange={() => {}} />, { wrapper: Wrapper });
    expect(screen.getByText("Create one for scripts and test benches.")).toBeTruthy();
  });
});
