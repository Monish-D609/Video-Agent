import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api calls are forwarded to the FastAPI server (no CORS setup needed)
export default defineConfig({
  plugins: [react()], // keep whatever your file already has here
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});