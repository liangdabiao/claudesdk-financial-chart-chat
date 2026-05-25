import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/ws": { target: "http://localhost:3015", ws: true },
      "/api": "http://localhost:3015",
      "/charts": "http://localhost:3015",
    },
    watch: {
      ignored: ["**/.claude/**", "**/server.log"],
    },
  },
});
