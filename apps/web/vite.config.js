/**
 * @file /apps/web/vite.config.ts
 *
 * @description
 * Vite build/runtime configuration for the frontend toolchain.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module is essential for build stability and deployment correctness.
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
    },
});
