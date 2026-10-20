import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: "0.0.0.0", port: 5100 },
  build: { chunkSizeWarningLimit: 800 }, // recharts is the bulk of the bundle
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
