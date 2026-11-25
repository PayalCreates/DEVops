/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, Vite proxies API calls to the FastAPI server so the browser sees one
// origin (same as production, where nginx does the proxying).
const backend = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/health': backend,
    },
  },
  // `vite preview` mirrors the production nginx headers so E2E tests behave the same.
  preview: {
    port: 4173,
    proxy: { '/api': backend, '/health': backend },
    headers: {
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
    },
  },
  build: {
    sourcemap: false,
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: { reporter: ['text', 'lcov'], include: ['src/**/*.{ts,tsx}'] },
  },
})
