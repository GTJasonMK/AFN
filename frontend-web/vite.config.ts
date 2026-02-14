import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const parsePort = (rawValue: string | undefined, fallbackPort: number): number => {
  const parsed = Number(rawValue)
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 65535) {
    return fallbackPort
  }
  return Math.trunc(parsed)
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // loadEnv 主要读取 .env 文件；同时合并 process.env，确保通过 start_web.py 注入的端口能被读取到
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }

  const frontendPort = parsePort(env.VITE_WEB_PORT, 5173)
  const backendPort = parsePort(env.VITE_BACKEND_PORT, 8123)
  const backendHost = (env.VITE_BACKEND_HOST || '127.0.0.1').trim() || '127.0.0.1'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '127.0.0.1',
      port: frontendPort,
      strictPort: true,
      proxy: {
        '/api': {
          target: `http://${backendHost}:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
