import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri expects a fixed dev port; `clearScreen: false` keeps Rust errors visible.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "127.0.0.1",
    // Only src/ is frontend code. sample_notes/ has a deliberate symlink loop
    // (edge-case test) that crashes the watcher; the rest is just wasted work.
    watch: {
      ignored: ["**/sample_notes/**", "**/backend/**", "**/src-tauri/**", "**/docs/**"],
    },
  },
  envPrefix: ["VITE_", "TAURI_ENV_"],
  build: {
    target: "es2020",
    sourcemap: false,
  },
});
