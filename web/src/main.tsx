import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { Tooltip } from "radix-ui";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";
import App from "./App";
import { ZynSprite } from "./components/icons";
import { JobsProvider } from "./lib/jobs";
import { ReviewerProvider, useReviewer } from "./lib/reviewer";
import "./styles/tokens.css";
import "./styles/app.css";

/** Toasts follow the app's own theme choice, not only the OS. */
function ThemedToaster() {
  const { theme } = useReviewer();
  return <Toaster position="bottom-right" theme={theme} closeButton toastOptions={{ className: "toast" }} />;
}

const qc = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <ReviewerProvider>
        <JobsProvider>
          {/* reducedMotion="user": every Motion animation respects the OS setting */}
          <MotionConfig reducedMotion="user">
            <Tooltip.Provider delayDuration={600}>
              <ZynSprite />
              <App />
              <ThemedToaster />
            </Tooltip.Provider>
          </MotionConfig>
        </JobsProvider>
      </ReviewerProvider>
    </QueryClientProvider>
  </StrictMode>,
);
