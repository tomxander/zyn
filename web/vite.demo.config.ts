import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The online demo: the real review screen with a stand-in API (demo/mock.ts) and recorded runs.
// Build with: npx vite build -c vite.demo.config.ts --base /zyn/demo/ --outDir <site dist>/demo
export default defineConfig({
  root: "demo",
  base: "./",
  publicDir: "public",
  plugins: [react()],
  build: { outDir: "../dist-demo", emptyOutDir: true, chunkSizeWarningLimit: 1200 },
});
