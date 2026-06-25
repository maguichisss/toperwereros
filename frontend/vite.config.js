import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';

const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:3001';

const httpsConfig =
  process.env.VITE_HTTPS_CERT && process.env.VITE_HTTPS_KEY
    ? {
        key: fs.readFileSync(process.env.VITE_HTTPS_KEY),
        cert: fs.readFileSync(process.env.VITE_HTTPS_CERT),
      }
    : false;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    https: httpsConfig,
    proxy: {
      '/api': proxyTarget,
      '/uploads': proxyTarget,
    },
    watch: {
      usePolling: true,
      ignored: ['**/node_modules/**'],
    },
  },
});
