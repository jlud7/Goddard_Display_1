import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://192.168.8.141",
        changeOrigin: true,
        timeout: 20000,
        proxyTimeout: 20000,
      },
      "/ws/frame": {
        target: "http://192.168.8.141",
        ws: true,
        changeOrigin: true,
        timeout: 20000,
        proxyTimeout: 20000,
      },
      "/ws/events": {
        target: "http://192.168.8.141",
        ws: true,
        changeOrigin: true,
        timeout: 20000,
        proxyTimeout: 20000,
      },
      "/render": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
      "/agent": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
      "/display": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
      "/catalog": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
      "/weather": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
    },
  },
});
