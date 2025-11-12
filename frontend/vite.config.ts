import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import svgr from 'vite-plugin-svgr'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), svgr()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    exclude: [
      'axios',
      'lucide-react',
      '@tanstack/react-query'
    ]
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            let clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
            if (clientIp.startsWith('::ffff:')) {
              clientIp = clientIp.replace('::ffff:', '');
            }
            proxyReq.setHeader('X-Forwarded-For', clientIp);
            proxyReq.setHeader('X-Real-IP', clientIp);
          });
        },
      },
      '/token': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            let clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
            if (clientIp.startsWith('::ffff:')) {
              clientIp = clientIp.replace('::ffff:', '');
            }
            proxyReq.setHeader('X-Forwarded-For', clientIp);
            proxyReq.setHeader('X-Real-IP', clientIp);
          });
        },
      },
      '/users': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            let clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
            if (clientIp.startsWith('::ffff:')) {
              clientIp = clientIp.replace('::ffff:', '');
            }
            proxyReq.setHeader('X-Forwarded-For', clientIp);
            proxyReq.setHeader('X-Real-IP', clientIp);
          });
        },
      },
    },
  },
})
