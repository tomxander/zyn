import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The Zyn website. Static: `npm run build` writes dist/, which any static host can serve.
// `npm run build:thomasalex` builds it to live at thomasalex.in/zyn (all URLs start with /zyn/).
export default defineConfig(({ mode }) => ({
  base: mode === "thomasalex" ? "/zyn/" : "/",
  plugins: [react()],
  // The docs pages read ../docs/wiki at build time; let the dev server read it too.
  server: { port: 5180, fs: { allow: [".."] } },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 900 },
}));
