import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    allowedHosts: [".e2b.app"],
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/legal": "http://127.0.0.1:8080",
      "/privacy": "http://127.0.0.1:8080",
      "/consent": "http://127.0.0.1:8080",
      "/guides": "http://127.0.0.1:8080",
      // Hashed styles and fonts linked by server-rendered documents after a UI build.
      "/assets": "http://127.0.0.1:8080",
    },
  },
});
