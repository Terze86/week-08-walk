import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Allow the forwarded address GitHub Codespaces gives the dev server.
    allowedHosts: [".app.github.dev"],
    proxy: { "/api": process.env.LIMS_API_URL ?? "http://localhost:8000" },
  },
});
