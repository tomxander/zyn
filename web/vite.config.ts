import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Dev: the Python API runs on 8600 (python -m harness serve --no-browser).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8600" } },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test-setup.ts"] },
});
